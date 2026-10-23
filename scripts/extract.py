#!/usr/bin/env python3
"""Deterministic extractor for video-to-skill v2.

Input: video URLs (any host yt-dlp/summarize supports) and/or local media files.
Output (in workdir):
  transcript.txt  -- timestamped transcript, chapter/topic demarcated
  metadata.json   -- sources, duration, words, est. tokens, chapters, provenance

Extraction ladder:
  1. summarize CLI (--extract --timestamps) -> fast, cloud/bot resilient
  2. yt-dlp (manual subs > auto subs > audio download)
  3. local Whisper transcription (faster-whisper > whisper CLI)

Stdlib-only dependencies; external binaries called via subprocess.
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

URL_RE = re.compile(r"^https?://")
TIMING_RE = re.compile(
    r"(\d{1,2}:)?(\d{1,2}):(\d{2})[.,](\d{3})\s*-->\s*(\d{1,2}:)?(\d{1,2}):(\d{2})[.,](\d{3})"
)
TAG_RE = re.compile(r"<[^>]+>")
BIDI_ZERO_RE = re.compile(r"[​-‏‪-‮⁠⁦-⁩]")

WORKDIR = Path(os.environ.get("VIDEO_SKILL_WORKDIR", Path(tempfile.gettempdir()) / "video_skill_work"))


def cue_seconds(h_m_s):
    h, m, s = h_m_s
    return (h or 0) * 3600 + m * 60 + s


def _ts_groups(m):
    """Return start_seconds from a TIMING_RE match."""
    start = (
        int(m.group(1)[:-1]) if m.group(1) else 0,
        int(m.group(2)),
        int(m.group(3)),
    )
    return cue_seconds(start)


def parse_vtt(text):
    """Parse WebVTT/SRT into [(start_seconds, caption_text)], keeping order."""
    cues = []
    pending = None
    for raw_line in text.splitlines():
        m = TIMING_RE.search(raw_line)
        if m:
            if pending:
                cues.append(pending)
            pending = (_ts_groups(m), "")
            continue
        line = TAG_RE.sub("", BIDI_ZERO_RE.sub("", raw_line)).strip()
        if pending is not None:
            if line.isnumeric():
                cues.append(pending)
                pending = None
            elif line:
                pending = (pending[0], (pending[1] + " " + line).strip())
    if pending:
        cues.append(pending)
    return [(s, t) for s, t in cues if t]


def parse_summarize_transcript(text):
    """Parse output from `summarize --extract --timestamps <url>`.
    Format is lines like:
    [0:00] text text
    [12:34] text text
    """
    cues = []
    ts_pattern = re.compile(r"^\[(?:(\d+):)?(\d{1,2}):(\d{2})\]\s*(.*)$")
    in_transcript = False
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("Transcript:"):
            in_transcript = True
            continue
        if not in_transcript and not line.startswith("["):
            continue
        m = ts_pattern.match(line)
        if m:
            h = int(m.group(1)) if m.group(1) else 0
            m_val = int(m.group(2))
            s = int(m.group(3))
            sec = h * 3600 + m_val * 60 + s
            txt = m.group(4).strip()
            if txt:
                cues.append((sec, txt))
        elif line and cues:
            # Continuation line
            last_sec, last_txt = cues[-1]
            cues[-1] = (last_sec, (last_txt + " " + line).strip())
    return cues


def dedupe_cues(cues):
    """Merge rolling auto-caption duplicates: collapse repeats inside one cue,
    and strip each cue's leading words already emitted as the prior cue's tail."""
    out = []
    last_words = []
    last_sec = None
    for sec, txt in cues:
        rolling = last_sec is not None and sec - last_sec <= 3.5
        parts = [p.strip() for p in txt.splitlines() if p.strip()] or [txt]
        seen_part = []
        for p in parts:
            prev = " ".join(last_words[-len(p.split()):]) if last_words else ""
            if not rolling or not prev or p != prev or (
                seen_part and p == seen_part[-1]
            ):
                if not seen_part or p != seen_part[-1]:
                    seen_part.append(p)
        merged = " ".join(seen_part).strip()
        words = merged.split()
        k = 0
        if rolling and last_words:
            max_k = min(len(words), len(last_words), 12)
            for i in range(max_k, 0, -1):
                if last_words[-i:] == words[:i]:
                    k = i
                    break
        remaining = words[k:]
        if remaining:
            out.append((sec, " ".join(remaining)))
            last_words = remaining
        last_sec = sec
    return out


def fmt_ts(seconds):
    seconds = int(seconds)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"[{h}:{m:02d}:{s:02d}]" if h else f"[{m:02d}:{s:02d}]"


def estimate_tokens(words):
    return int(words * 1.3)


def run(cmd, **kw):
    return subprocess.run([str(c) for c in cmd], capture_output=True, text=True, **kw)


def have(binary):
    return bool(shutil.which(binary))


def fetch_summarize_url(url):
    """Attempt fetch using summarize CLI (handles bot blocks and fast text extract)."""
    summarize_bin = shutil.which("summarize") or os.path.expanduser("~/.local/bin/summarize")
    if not (os.path.exists(summarize_bin) or have("summarize")):
        return None, None
    r = run([summarize_bin, "--extract", "--timestamps", url], timeout=90)
    if r.returncode == 0 and "Transcript:" in r.stdout:
        cues = parse_summarize_transcript(r.stdout)
        if cues:
            return cues, "summarize-cli"
    return None, None


def fetch_ytdlp_url(url, dest):
    """Download subs (manual preferred, then auto) + info json via yt-dlp."""
    base = dest / "src"
    r = run([
        "yt-dlp", "--skip-download", "--no-warnings",
        "--write-info-json",
        "--write-subs", "--write-auto-subs",
        "--sub-langs", "en.*,en,en-orig",
        "--sub-format", "vtt/srt/best",
        "-o", str(base) + ".%(ext)s",
        url,
    ])
    info_path = Path(str(base) + ".info.json")
    info = json.loads(info_path.read_text(encoding="utf-8")) if info_path.exists() else {}
    
    sub_files = sorted(dest.glob("src*.vtt")) + sorted(dest.glob("src*.srt"))
    manual = [f for f in sub_files if ".auto." not in f.name]
    picked = None
    kind = None
    if manual:
        picked, kind = manual[0], "manual-subs"
    elif sub_files:
        picked, kind = sub_files[0], "auto-subs"
    return info, (picked.read_text(encoding="utf-8") if picked else None), kind


WHISPER_HINT = (
    "No subtitle track and no local speech-to-text engine found.\n"
    "Install one, then rerun:\n"
    "  pip3 install faster-whisper     (recommended)\n"
    "  # or: brew install whisper-cpp && brew install ffmpeg"
)


def transcribe_audio(media_path, dest, install_missing):
    """Fallback ASR path. Returns [(seconds, text)] or raises with guidance."""
    wav = dest / "audio.wav"
    r = run(["ffmpeg", "-y", "-i", media_path, "-vn", "-ac", "1", "-ar", "16000", wav])
    if r.returncode != 0:
        raise RuntimeError(f"ffmpeg failed:\n{(r.stderr or '')[-1000:]}\nIs ffmpeg installed?")
    try:
        import io

        buf = io.StringIO()
        from faster_whisper import WhisperModel  # noqa: PLC0415

        model = WhisperModel("small", device="cpu", compute_type="int8")
        segments, info = model.transcribe(str(wav))
        for seg in segments:
            buf.write(f"{seg.start:.1f}|{seg.text.strip()}\n")
        lines = buf.getvalue()
        lang = getattr(info, "language", "") or ""
    except ImportError:
        if have("whisper"):
            out_dir = dest / "asr"
            r = run(["whisper", "--model", "small", "--output_format", "txt",
                     "--output_dir", out_dir, wav])
            if r.returncode != 0:
                raise RuntimeError(f"whisper CLI failed:\n{(r.stderr or '')[-1000:]}")
            txt_file = next(out_dir.glob("*.txt"), None)
            lines = ""
            if txt_file:
                lines = txt_file.read_text(encoding="utf-8")
            lang = ""
        elif install_missing == "yes":
            r = run([sys.executable, "-m", "pip", "install", "--user", "faster-whisper"])
            if r.returncode == 0:
                return transcribe_audio(media_path, dest, "no")
            raise RuntimeError(WHISPER_HINT + f"\npip install failed:\n{r.stderr[-500:]}")
        else:
            raise RuntimeError(WHISPER_HINT)
    cues = []
    for line in lines.splitlines():
        if "|" in line:
            sec, txt = line.split("|", 1)
            try:
                cues.append((float(sec), txt.strip()))
            except ValueError:
                continue
    return cues, lang


def download_media(url, dest):
    r = run(["yt-dlp", "--no-warnings", "-f", "bestaudio/best", "-o", str(dest / "media.%(ext)s"), url])
    if r.returncode != 0:
        raise RuntimeError(f"yt-dlp media download failed:\n{(r.stderr or '')[-800:]}")
    files = [f for f in dest.glob("media.*") if f.suffix != ".part"]
    return files[0]


def get_video_info(url):
    """Extract metadata json from URL without downloading media."""
    r = run(["yt-dlp", "--dump-single-json", "--no-warnings", url])
    if r.returncode == 0 and r.stdout.strip():
        try:
            return json.loads(r.stdout)
        except Exception:
            pass
    return {}


def process_url(url, sources):
    src_dir = WORKDIR / f"url_{len(sources)}"
    src_dir.mkdir(parents=True, exist_ok=True)
    
    cues = None
    kind = None
    info = {}
    title = url
    lang = "en"
    chapters = []
    
    # 1. Try summarize CLI first (fast and circumvents YouTube bot 429)
    cues, kind = fetch_summarize_url(url)
    if cues:
        info = get_video_info(url)
        title = info.get("title") or url
        chapters = info.get("chapters") or []
        lang = info.get("language") or "en"
    else:
        # 2. Try yt-dlp subtitle extraction
        try:
            info, sub_text, yt_kind = fetch_ytdlp_url(url, src_dir)
            if sub_text:
                cues = dedupe_cues(parse_vtt(sub_text))
                kind = yt_kind
                lang = info.get("language") or "en"
                chapters = info.get("chapters") or []
                title = info.get("title") or url
        except Exception as e:
            print(f"  yt-dlp sub fetch failed: {e}", file=sys.stderr)

    # 3. Fallback to audio download + Whisper
    if not cues:
        print(f"  no subtitles for {url!r}; falling back to local transcription...", file=sys.stderr)
        media = download_media(url, src_dir)
        cues, lang = transcribe_audio(media, src_dir, INSTALL_MODE)
        kind = "whisper"
        if not info:
            info = get_video_info(url)
        title = info.get("title") or url
        chapters = info.get("chapters") or []

    register_source(sources, {
        "kind": "url", "url": url, "title": title,
        "uploader": info.get("uploader") or info.get("channel") or "",
        "duration_s": info.get("duration") or (int(cues[-1][0]) if cues else 0),
        "language": lang,
        "transcript_source": kind,
    }, cues, chapters)
    return info


def process_file(path, sources):
    path = Path(path).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(path)
    src_dir = WORKDIR / f"file_{len(sources)}"
    src_dir.mkdir(parents=True, exist_ok=True)
    print(f"  transcribing {path.name} locally (this can take a while)...", file=sys.stderr)
    cues, lang = transcribe_audio(path, src_dir, INSTALL_MODE)
    register_source(sources, {
        "kind": "file", "path": str(path), "title": path.stem,
        "uploader": "", "duration_s": int(cues[-1][0]) if cues else None,
        "language": lang, "transcript_source": "whisper",
    }, cues, [])


def register_source(sources, meta, cues, chapters):
    words = sum(len(t.split()) for _, t in cues)
    meta.update({"words": words, "est_tokens": estimate_tokens(words)})
    sources.append(meta)
    with open(WORKDIR / "transcript.txt", "a", encoding="utf-8") as fh:
        fh.write(f"\n=== SOURCE: {meta['title']} ({meta['transcript_source']}) ===\n")
        ch_starts = [(int(c.get("start_time") or 0), c.get("title") or "Chapter") for c in chapters]
        ch_i = 0
        for sec, txt in cues:
            while ch_i < len(ch_starts) and sec >= ch_starts[ch_i][0]:
                cs, ct = ch_starts[ch_i]
                ce = int(chapters[ch_i].get("end_time") or 0)
                fh.write(f"\n--- CHAPTER: {ct} {fmt_ts(cs)}-{fmt_ts(ce)} ---\n")
                ch_i += 1
            fh.write(f"{fmt_ts(sec)} {txt}\n")


def preflight():
    rows = [
        ("summarize (cli)", have("summarize") or os.path.exists(os.path.expanduser("~/.local/bin/summarize"))),
        ("yt-dlp", have("yt-dlp")),
        ("ffmpeg", have("ffmpeg")),
        ("faster-whisper (python)", False),
    ]
    try:
        import faster_whisper  # noqa: F401
        rows[-1] = ("faster-whisper (python)", True)
    except ImportError:
        pass
    rows.insert(3, ("whisper (cli)", have("whisper")))
    for name, ok in rows:
        print(f"  {'✓' if ok else '✗'} {name}")
    print("\nURLs prefer summarize CLI or yt-dlp. Local files need ffmpeg + an ASR engine.")


def main(argv=None):
    global INSTALL_MODE
    ap = argparse.ArgumentParser(prog="video-to-skill-extract")
    ap.add_argument("inputs", nargs="*", help="video URLs and/or local media files")
    ap.add_argument("--check", action="store_true", help="print environment report and exit")
    ap.add_argument("--install-missing", choices=["ask", "yes", "no"], default="ask")
    ns = ap.parse_args(argv)
    INSTALL_MODE = ns.install_missing

    if ns.check:
        preflight()
        return 0
    if not ns.inputs:
        ap.error("video-to-skill requires a video URL or local media path")

    shutil.rmtree(WORKDIR, ignore_errors=True)
    WORKDIR.mkdir(parents=True, exist_ok=True)
    sources = []
    failures = []
    for inp in ns.inputs:
        try:
            if URL_RE.match(inp):
                process_url(inp, sources)
            else:
                process_file(inp, sources)
        except Exception as exc:
            failures.append((inp, str(exc)))
            print(f"  ⚠ skipped {inp}: {exc}", file=sys.stderr)
    if not sources:
        for inp, err in failures:
            print(f"error: {inp}: {err}", file=sys.stderr)
        return 1

    total_words = sum(s["words"] for s in sources)
    meta = {
        "sources": sources,
        "total_words": total_words,
        "total_est_tokens": estimate_tokens(total_words),
        "failures": [{"input": i, "error": e} for i, e in failures],
    }
    (WORKDIR / "metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(json.dumps({
        "workdir": str(WORKDIR),
        "sources": len(sources),
        "est_tokens": meta["total_est_tokens"],
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
