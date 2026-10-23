---
name: video-to-skill
description: "Turn any video, talk, lecture, or tutorial into a structured, evidence-grounded agent skill for Hermes, Claude Code, or Codex. Extracts frameworks, mental models, actionable steps, demos, and anti-patterns with exact timestamps and seen/guessed/unknown evidence labels."
---

<!-- argument-hint: <video-url-or-media-path>... [skill-name-slug] [--host hermes|claude|codex] -->

# Video-to-Skill Converter (v2)

Transform spoken and demonstrated knowledge into actionable agent skills by extracting structure, preserving exact timestamps, and labeling evidence provenance (`seen`, `guessed`, `unknown`).

Modeled on [book-to-skill](https://github.com/virgiliojr94/book-to-skill) and enhanced with evidence grounding principles inspired by [REA](https://github.com/morluto/rea).

## Philosophy

Videos contain crystallized expertise: frameworks, live demos, architectural decisions, war stories, and edge-case gotchas. This tool extracts that knowledge into a skill your agent loads on demand.

**1. Extract structure, not summaries.** A skill isn't a recap. It is a toolkit of:
- Named frameworks and mental models (with timestamp citations `[mm:ss]`)
- Step-by-step techniques and decision matrices
- Demos and worked examples (what was shown, inputs, outputs, observable behavior)
- Anti-patterns and smells (what the speaker warns against and why)

**2. Evidence Provenance (`seen` | `guessed` | `unknown`).** A guess must never pass as a fact.
- `[seen]`: Directly demonstrated or spoken in the source with verifiable timestamp proof.
- `[guessed]`: Inferred from context, surrounding code, or known platform conventions.
- `[unknown]`: Unstated by speaker/author, unresolved backend state, or closed-source details.

**3. Preserve timestamps.** Every framework links back to `[mm:ss]` so you can re-watch 90 seconds instead of scrubbing through an hour.

**4. Host-aware installation.** Installs natively for:
- Hermes: `~/.hermes/skills/<category>/<skill-name>/`
- Claude Code: `~/.claude/skills/<skill-name>/`
- Codex: `~/.codex/skills/<skill-name>/`

---

## Modes of Operation

1. **Full Conversion (Default)**: Given URL(s) or file(s), extract transcripts, analyze structure, author modular segments, supporting files, and validate.
2. **Analyze Only**: Extract transcript, emit extraction report with frameworks and detected segments, stop.
3. **Fold-in / Update**: Append or integrate a new source into an existing skill.

---

## Skill Architecture

Every generated skill package contains:

| File | Purpose |
|---|---|
| `SKILL.md` | Core frameworks + segment/topic index (<=4k tokens, front-loaded) |
| `segments/segNN-*.md` | Chapter/topic deep-dives, loaded on-demand, timestamp-cited |
| `cheatsheet.md` | Fast decision rules, thresholds, trade-off matrices, tells |
| `patterns.md` | Reusable technical patterns and step-by-step techniques |
| `glossary.md` | Key terms and definitions with timestamp references |
| `timestamps.md` | Full jump list back into the source video |
| `sources.md` | Source metadata, duration, uploader, channel, transcript source |

---

## Workflow Steps

### Step 1: Preflight & Environment Check

```bash
python3 scripts/extract.py --check
```

Validates availability of `summarize` CLI, `yt-dlp`, `ffmpeg`, and Whisper backends.

### Step 2: Deterministic Extraction

```bash
python3 scripts/extract.py <INPUTS>
```

Ladder:
1. `summarize` CLI (fast transcript + timestamp extraction, bypasses bot blocks)
2. `yt-dlp` (manual subs > auto subs > audio download)
3. Local Whisper ASR fallback

Creates `transcript.txt` and `metadata.json` in working directory.

### Step 3: Analyze & Structure

Read transcript, identify speaker, topics, chapter timestamps, and core takeaways.
Categorize findings by:
- Frameworks & Mental Models
- Techniques & Methods
- Demos & Examples
- Anti-patterns & Caveats

### Step 4: Author Artifacts with Evidence Grounding

When authoring, apply the strict evidence rule to every bullet:
```markdown
- **<Framework Name>** [mm:ss] [seen]: <Core rule and why it works>
- *Heuristic* [mm:ss] [guessed]: <Inferred optimization based on behavior>
- *Limitation* [mm:ss] [unknown]: <Server-side logic not disclosed>
```

### Step 5: Validate Package

```bash
python3 scripts/validate.py <path-to-generated-skill>
```

The validator verifies:
- YAML frontmatter completeness
- No raw media files packaged
- No private absolute home paths leaked
- Presence of timestamp citations `[mm:ss]`
- Presence of evidence grounding labels `[seen|guessed|unknown]`

---

## Quality Rules

1. Extract structure, not play-by-play narrative.
2. Preserve speaker's exact naming and terminology.
3. Every claim carries `[mm:ss]` and `[seen|guessed|unknown]`.
4. Distinguish demonstrated capability from verbal claims.
5. Keep `SKILL.md` front-loaded and lean (<=4,000 tokens). Detailed segments load on demand.
6. Verify against `validate.py` before completing installation.

---

## Skill Extension: How to Generate More Specialized Skills

`video-to-skill` adapts to different content genres by tailoring which artifacts are emphasized:

### 1. Reverse-Engineering & Architecture Skills (like REA)
- **Primary Source**: Technical deep dives, security audits, decompilations.
- **Key Artifacts**: Trace contracts, network payloads, API boundaries, and `cheatsheet.md` decision trees.
- **Evidence Rule**: Tag client-side observations as `[seen]`, inferred architecture as `[guessed]`, closed backends as `[unknown]`.

### 2. Engineering Leadership & Process Skills (like Anthropic Claude Code)
- **Primary Source**: Conference talks, developer workflows, system design retrospectives.
- **Key Artifacts**: High-altitude mental models (`SKILL.md`), specialist meta-prompts, review loops, and multidisciplinary checklists.
- **Evidence Rule**: Focus on verified outcomes and empirical rules of thumb.

### 3. Production Playbook Skills (like Vercel CEO)
- **Primary Source**: Founder interviews, post-mortems, scaling guides.
- **Key Artifacts**: Operational invariants (`AGENTS.md` rules), adversarial breaker scripts, direction audits, and anti-drift commands.
- **Evidence Rule**: Distinguish personal heuristics from hard system invariants.

### 4. UI/UX & Frontend Design System Skills (like Top 6 AI Design Repos & Google Stitch)
- **Primary Source**: Tool showcases, design system demos, frontend tutorials.
- **Key Artifacts**: Component tokens (`design.md`), multi-viewport testing scripts, motion/animation formulas, and CLI automation.
- **Evidence Rule**: Ground every style recommendation in verifiable CSS parameters or tool outputs.

### Generating Any New Custom Skill: One Command
```bash
# In Hermes / Claude Code:
/video-to-skill <video-or-course-url> [custom-skill-name]
```
The extractor will automatically fetch the clean transcript, map chapter timestamps, author modular segments with evidence labels, and run mechanical validation before saving to your skills library.
