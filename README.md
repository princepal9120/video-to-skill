# video-to-skill (v2)

Turn any video into an evidence-grounded agent skill for Hermes, Claude Code, or Codex.

Point it at a YouTube URL (or any yt-dlp-supported video) or local media file, and get back an on-demand knowledge base of the speaker's frameworks, techniques, demos, and anti-patterns. Every claim is cited with an exact timestamp `[mm:ss]` and tagged with strict evidence provenance (`[seen]`, `[guessed]`, `[unknown]`).

Modeled on [book-to-skill](https://github.com/virgiliojr94/book-to-skill) and enhanced with evidence grounding inspired by [REA](https://github.com/morluto/rea).

## Key Features

- **Multi-Host Native Support**: Installs for Hermes Agent (`~/.hermes/skills/`), Claude Code (`~/.claude/skills/`), or Codex (`~/.codex/skills/`).
- **Resilient Multi-Engine Extraction**: Automated fallback ladder:
  1. `summarize` CLI (fast transcript + timestamps, bypasses YouTube 429 bot checks)
  2. `yt-dlp` (manual subs > auto subs > audio download)
  3. Local Whisper ASR fallback (faster-whisper or whisper CLI)
- **Evidence Provenance (`seen` | `guessed` | `unknown`)**: Prevents auto-caption hallucinations and ASR mishearings from masquerading as verified facts.
- **Built-in Validation Harness**: `scripts/validate.py` enforces frontmatter structure, timestamp presence, evidence labels, and sanitization of private paths.
- **Timestamp Citations**: Every framework and technique links back to `[mm:ss]` so you can jump straight to the relevant clip.

## Install

```bash
# Add to Claude Code:
git clone https://github.com/princepal9120/video-to-skill.git ~/.claude/skills/video-to-skill

# Or add to Hermes Agent:
git clone https://github.com/princepal9120/video-to-skill.git ~/.hermes/skills/content-creation/video-to-skill
```

## Usage

```bash
# In Hermes / Claude Code:
/video-to-skill https://www.youtube.com/watch?v=rw0fqnrZgNM rea-reverse-engineer-anything
```

### Deterministic Extraction CLI

You can also run the extractor standalone:

```bash
# Check system dependencies
python3 scripts/extract.py --check

# Extract transcript and metadata
python3 scripts/extract.py https://www.youtube.com/watch?v=rw0fqnrZgNM
```

### Validation

```bash
python3 scripts/validate.py path/to/generated-skill
```

## Package Output Structure

| File | Purpose |
|---|---|
| `SKILL.md` | Core frameworks + topic index (<=4k tokens, front-loaded) |
| `segments/segNN-*.md` | Detailed chapter & topic deep-dives |
| `cheatsheet.md` | Decision rules, trade-off matrices, heuristics |
| `patterns.md` | Step-by-step techniques and execution patterns |
| `glossary.md` | Domain terminology with timestamp links |
| `timestamps.md` | Complete jump list back to source video |
| `sources.md` | Verification provenance and transcript source metadata |

## Dependencies

- `summarize` CLI (recommended) — `npm i -g @steipete/summarize`
- `yt-dlp` — `brew install yt-dlp`
- `ffmpeg` — `brew install ffmpeg`
- `faster-whisper` (optional ASR fallback) — `pip3 install faster-whisper`

## License

MIT
