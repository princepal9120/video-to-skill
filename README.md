# video-to-skill

Turn any video into a structured agent skill for Claude Code. Point it at a YouTube URL (or any yt-dlp-supported host) or a local audio/video file, and get back an on-demand knowledge base of the speaker's frameworks, techniques, demos, and anti-patterns — every claim cited with a timestamp.

Modeled on [book-to-skill](https://github.com/virgiliojr94/book-to-skill) (books → skills); this one does spoken knowledge: talks, tutorials, lectures, podcasts, courses.

## Install

```bash
npx skills add princepal9120/video-to-skill
# or clone directly:
git clone https://github.com/princepal9120/video-to-skill.git ~/.claude/skills/video-to-skill
```

## Usage

In Claude Code (restart the session after installing):

```
/video-to-skill https://www.youtube.com/watch?v=Ch4Sl0POBhU ralston-personal-brand
```

The skill walks the pipeline: preflight → transcript extraction → cost estimate → segment conversion → master SKILL.md with topic index.

## What you get

| File | Purpose |
|------|---------|
| `SKILL.md` | Core frameworks + segment/topic index (≤4k tokens, front-loaded) |
| `segments/segNN-*.md` | One file per chapter/segment, loaded on-demand, timestamp-cited |
| `timestamps.md` | Jump list back into the source video |

Key differentiator vs reading a transcript dump: **every framework links back to `[mm:ss]`** so you re-watch 90 seconds instead of re-watching 6 hours.

## How it works

Two halves, same architecture as book-to-skill:

1. **Deterministic extractor** (`scripts/extract.py`, stdlib-only Python) — downloads subtitles via yt-dlp (manual subs > auto subs), falls back to local Whisper transcription when no subs exist, parses/dedupes cues, demarcates chapters, writes `transcript.txt` + `metadata.json`.
2. **Spec-driven generator** (`SKILL.md` workflow) — your agent follows the spec to convert transcripts into structured skill files: extract structure, not summaries; preserve the speaker's exact terminology; distinguish asserted vs demonstrated claims.

## Dependencies

- `yt-dlp` (URLs) — `brew install yt-dlp`
- `ffmpeg` (local files / Whisper fallback) — `brew install ffmpeg`
- `faster-whisper` (optional ASR fallback) — `pip3 install faster-whisper`

Check your environment anytime:

```bash
python3 ~/.claude/skills/video-to-skill/scripts/extract.py --check
```

## Example output

Converting Caleb Ralston's 6h22m personal-branding course produced [`ralston-personal-brand`](https://github.com/princepal9120/ralston-personal-brand): 30 timestamp-cited segment files across Branding/Content/Team/Monetize, master SKILL.md with topic index (~98k source tokens distilled into on-demand files).

## Scope & limits

Transcripts from auto-captions/Whisper contain recognition errors — verify exact wording against timestamps before quoting. Covers spoken content only (no visual demo analysis).

## License

MIT
