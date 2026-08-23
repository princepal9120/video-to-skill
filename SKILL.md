---
name: video-to-skill
description: "Converts videos (YouTube and any yt-dlp-supported URL, local audio/video files) into structured agent skills, extracting the speaker's frameworks, techniques, claims, demos, and anti-patterns from transcripts. Use when the user wants to study a talk, tutorial, lecture, podcast, or course video through Claude Code, apply the speaker's methods while working, or build a reusable knowledge base from a video."
---

<!-- argument-hint: <video-url-or-media-path>... [skill-name-slug] -->

# Video-to-Skill Converter

Transform spoken knowledge (talks, tutorials, lectures, podcasts, courses) into actionable agent skills by extracting structure — not producing summaries. Modeled on [book-to-skill](https://github.com/virgiliojr94/book-to-skill).

## Philosophy

Videos contain crystallized expertise: frameworks, live demos, war stories, and Q&A that took years to develop. This skill extracts that knowledge into a skill your agent loads on demand.

**Extract structure, not summaries.** A skill isn't a recap. It's a toolkit of:
- Named frameworks and mental models (with timestamps)
- Actionable principles and step-by-step techniques
- Demos and worked examples (what was shown, what happened)
- Claims with evidence (and which were asserted vs demonstrated)
- Anti-patterns (what the speaker says to avoid and why)

**Preserve timestamps.** Timestamps are this skill's superpower over book-to-skill: every framework links back to the exact moment in the source so you can re-watch 90 seconds instead of re-watching an hour.

**Layer depth appropriately.** A 15-min talk → one lean SKILL.md. A 10-hour course → chapters/ + glossary + patterns + cheatsheet.

---

## Modes of Operation

Route on what the user asks:

1. **Full Conversion (Default)** — user provides URL(s)/path(s): run Steps 0–9.
2. **Analyze Only** — user says "analyze"/"just extract": run Steps 0–4, produce extraction report, stop.
3. **Generate from Prior Analysis** — user has analysis notes: skip to Step 6.
4. **Update / Fold-in** — new sources into existing skill: Steps 0–2, then fold-in workflow.

---

## Skill Location

Write generated skills to `~/.claude/skills/` (Claude Code). If `.claude/skills/` exists in the project and the user asked for project-local output, use that instead.

Helper script location: `~/.claude/skills/video-to-skill/scripts/extract.py` (probe `.claude/skills/video-to-skill/scripts/extract.py` project-local first).

---

## Step 0 — Out-of-scope check

No arguments → stop: "video-to-skill requires a video URL (any yt-dlp-supported host) or local media path. Usage: `video-to-skill <url-or-path>... [skill-name-slug]`".

Last arg that is neither an existing path nor a URL and looks like a slug (`[a-z0-9-]+`) → `SKILL_NAME`. Everything else → `INPUTS`.

If `SKILL_NAME` matches an existing skill folder containing a `SKILL.md`, flag as Update/Fold-in.

---

## Step 1 — Validate input & preflight

Run:

```bash
python3 ~/.claude/skills/video-to-skill/scripts/extract.py --check
```

URLs need `yt-dlp`. Local files need `ffmpeg` + an ASR engine (`faster-whisper` pip package preferred, `whisper` CLI fallback). If a required tool is missing for the given input type, stop and tell the user the exact install command before proceeding.

---

## Step 2 — Extract transcript

```bash
python3 <script_path> <INPUTS> --install-missing ask
```

Creates `<workdir>/transcript.txt` (timestamped, chapter-demarcated) and `<workdir>/metadata.json`. Read metadata.json.

Transcript preference per URL: manual subs > auto subs > local Whisper transcription (auto-downloads bestaudio via yt-dlp). The transcript records which source was used.

---

## Step 2.5 — Pre-flight cost estimate

Present before generating:

```
🎥 Sources: <N> (<list titles + durations>)
📝 Transcript: ~<words> words | ~<est_tokens>K tokens (source: manual subs / auto subs / whisper)

💰 Estimated cost:
   Input  (~1.3× tokens × passes): ~<N>K tokens
   Output (skill files):           ~<N>K tokens
   ⏱ Whisper fallback adds real transcription time (~real-time ÷ 5 on CPU)

📁 Generates: SKILL.md (+ chapters/, glossary.md, patterns.md, cheatsheet.md if large)

➡ Proceed? ("analyze only" to preview first)
```

Wait for confirmation unless user already said "go/end-to-end/full".

---

## Step 2.6 — REPL-style access for long transcripts (>50k tokens)

Same discipline as book-to-skill: treat `transcript.txt` as queryable corpus.

```bash
wc -w "$TRANSCRIPT"                                  # size check first
grep -n -E "^--- CHAPTER|^===" "$TRANSCRIPT"          # map offsets
sed -n '<start>,<end>p' "$TRANSCRIPT"                 # pull one section only
grep -c -i "<framework-name>" "$TRANSCRIPT"           # verify claim exists
```

Use targeted `Read(file, offset, limit)` — never dump a long transcript whole.

---

## Step 3 — Analyze structure

Read first ~8k chars of transcript.txt:
- Title, speaker(s), channel/source, duration
- Chapter markers (YouTube chapters land as `--- CHAPTER:` lines; talks may have none — segment by topic shifts instead)
- Core subject, approximate segments

**Analyze-only mode:** emit extraction report now:

```md
## Extraction Report — <Title>
### Speaker's Core Frameworks   - **<Name>**: what + when to apply [mm:ss]
### Key Principles              - <rule> [mm:ss]
### Techniques & Methods        - <step-by-step> [mm:ss]
### Demos & Worked Examples     - what was shown, outcome [mm:ss]
### Claims (asserted vs demonstrated)
### Anti-patterns               - avoid X because Y [mm:ss]
### Suggested Skill Name        `<speaker>-<concept>`
### Segments Detected | # | Topic | Timestamps | Frameworks |
```

---

## Step 4 — Ask purpose (Full Conversion only)

> "What should this skill help you do?
> 1. Apply the speaker's frameworks while working
> 2. Think with their mental models
> 3. Reference specific segments/timestamps
> 4. All of the above"

Only option 3 → `DEPTH=reference`; otherwise `DEPTH=study`.

Segment budget matrix (per file):

| | reference | study |
|---|---|---|
| text-heavy (podcast, interview) | 800–1,200 tok | 1,000–1,800 tok |
| technical (tutorial, demo) | 1,200–1,800 tok | 2,000–3,000 tok |

Study depth must be earned: reproduce one worked example/demo per segment, expand How into steps, add why-it-works notes. Never pad.

Skill name: propose `{speaker-lastname}-{concept}` (e.g. `norman-doors`) or `{title}-slug`. Confirm choice once; remember answer.

---

## Step 5 — Create structure

```bash
mkdir -p ~/.claude/skills/<skill_name>/segments
```

(For single short videos ≤30 min: skip segments/, everything lives in SKILL.md.)

---

## Step 6 — Generate segment files

One file per major segment/chapter: `segments/seg<NN>-<slug>.md`

```markdown
# Segment N: <Title> [<mm:ss>–<mm:ss>]

## Core Idea
<the single most important thing taught here>

## Frameworks Introduced
- **<Name>**: exact formulation [mm:ss]
  - When to use / How

## Key Concepts
- **Term**: definition (5–10 max)

## Demos & Examples *(technical)*
- What was shown at [mm:ss], inputs → outputs, what to notice

## Anti-patterns
- **Avoid X**: why it fails [mm:ss]

## Key Takeaways
1–7 actionable insights

## Connects To
- Seg N / external concepts
```

Technical emphasis → preserve commands/code verbatim in fenced blocks (spoken code ≠ written code; reconstruct carefully, mark reconstructions). Text emphasis → stories become "Use X when Y" heuristics.

---

## Step 7 — Supporting files (multi-segment skills only)

- **glossary.md** — terms alphabetically with timestamp refs: `**Term** — def [mm:ss]` (≤1,500 tok)
- **patterns.md** — techniques: When/How/Trade-offs + timestamp (≤2,000 tok)
- **cheatsheet.md** — decision rules, thresholds, trade-off tables, tells. Judgment layer, not keyword list (≤1,200 tok)
- **timestamps.md** — full clickable index `[mm:ss] → topic` for jumping back to source

---

## Step 8 — Master SKILL.md (≤4,000 tokens, front-load)

```markdown
---
name: <skill_name>
description: "Knowledge base from \"<Title>\" by <Speaker> (<duration>). Use when applying <speaker>'s frameworks for <topics>, studying the talk, or referencing its concepts."
---

# <Title>
**Speaker**: <name> | **Source**: <platform/urls> | **Duration**: <hh:mm> | **Generated**: YYYY-MM-DD

## How to Use This Skill
- No arguments → core frameworks
- Topic → read matching segment file, answer with timestamps
- `seg03` → load that segment
- "where do they talk about X" → timestamps.md jump list

## Core Frameworks & Mental Models
~2,000 tokens of the speaker's most important named ideas, written "Use X when Y", each with timestamp.

## Segment Index
| # | Topic | Time | File |
|--segment table with links--|

## Topic Index
- **Term** → segNN (alphabetical)

## Supporting Files
glossary.md · patterns.md · cheatsheet.md · timestamps.md

## Scope & Limits
Covers spoken content of these videos only. Transcripts from auto-subs/Whisper may contain recognition errors — verify exact wording against the timestamp before quoting.
```

---

## Step 9 — Cleanup and report

```bash
python3 -c "import shutil,tempfile,os; shutil.rmtree(os.environ.get('VIDEO_SKILL_WORKDIR', tempfile.gettempdir()+'/video_skill_work'), ignore_errors=True)"
```

Report:

```
✅ Skill created: ~/.claude/skills/<skill_name>/
🎥 <Title> — <Speaker> | <duration> | transcript via <manual/auto/whisper>

Files: SKILL.md (~X tok) · segments/ (N files) · glossary · patterns · cheatsheet · timestamps
Total: ~X tokens (loaded on-demand)

Usage:
  Ask about <topic>            → answer with timestamp citations
  "Where do they cover X?"     → jump list from timestamps.md
```

---

## Quality Rules

1. Extract structure, not summaries — frameworks, decisions, demos; not play-by-play
2. Preserve the speaker's precision — their names for things, exactly
3. Every claim carries a timestamp — this is the differentiator vs book-to-skill
4. Distinguish asserted vs demonstrated — a demo at [12:40] outranks a claim at [3:10]
5. Density over completeness — synthesize, never paste transcript walls
6. Auto-subs/Whisper introduce ASR errors — normalize obvious misrecognitions, flag uncertain quotes
7. Front-load SKILL.md; segment files stay on-demand
8. Topic index is critical — it's how the agent navigates

## Update / Fold-in

New sources into existing skill: extract new transcripts, match content against existing segments (revise vs append starting after highest seg number), merge glossary/patterns/cheatsheet/timestamps, regenerate master SKILL.md indexes, report.
