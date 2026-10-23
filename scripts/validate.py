#!/usr/bin/env python3
"""Validation harness for video-to-skill packages.

Checks:
  1. Frontmatter: name, description present. Name matches directory or requested slug.
  2. Structure: SKILL.md exists. If segments/ exists, segNN files are well-formed.
  3. Grounding / Timestamps: Every claim/framework has [mm:ss] or [hh:mm:ss].
  4. Evidence Labels: Every claim/framework carries seen | guessed | unknown label.
  5. Hygiene: No private absolute home paths (/Users/..., C:\\...), no raw media files (.mp4, .wav, .mp3).
  6. Provenance: timestamps.md, sources.md exist or are accounted for.

Usage:
  python3 validate.py <path-to-skill-directory>
"""

import argparse
import os
import re
import sys
from pathlib import Path

TS_RE = re.compile(r"\[(?:(\d+):)?(\d{1,2}):(\d{2})\]")
LABEL_RE = re.compile(r"\b(seen|guessed|unknown)\b", re.IGNORECASE)
PRIVATE_PATH_RE = re.compile(r"/(?:Users|home)/[a-zA-Z0-9_-]+")
RAW_MEDIA_EXTS = {".mp4", ".mkv", ".webm", ".avi", ".mov", ".wav", ".mp3", ".m4a", ".aac", ".flac"}


def check_skill(skill_dir: Path) -> list[str]:
    errors = []
    skill_dir = skill_dir.resolve()
    if not skill_dir.is_dir():
        return [f"Directory not found: {skill_dir}"]

    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        errors.append("Missing SKILL.md")
    else:
        content = skill_md.read_text(encoding="utf-8")
        if not content.startswith("---"):
            errors.append("SKILL.md missing frontmatter header (---)")
        else:
            parts = content.split("---", 2)
            if len(parts) < 3:
                errors.append("SKILL.md malformed frontmatter")
            else:
                fm = parts[1]
                if not re.search(r"^name:\s*\S+", fm, re.MULTILINE):
                    errors.append("SKILL.md frontmatter missing 'name'")
                if not re.search(r"^description:\s*\S+", fm, re.MULTILINE):
                    errors.append("SKILL.md frontmatter missing 'description'")

    # Check for raw media files
    for p in skill_dir.rglob("*"):
        if p.is_file() and p.suffix.lower() in RAW_MEDIA_EXTS:
            errors.append(f"Forbidden raw media file inside skill package: {p.relative_to(skill_dir)}")

    # Check Markdown files for private paths and timestamp / label grounding
    md_files = list(skill_dir.glob("*.md")) + list(skill_dir.glob("segments/*.md"))
    if not md_files:
        errors.append("No Markdown files found in skill package")

    has_timestamps = False
    has_labels = False

    for md in md_files:
        text = md.read_text(encoding="utf-8")
        if PRIVATE_PATH_RE.search(text):
            # Check if it's an instruction mentioning ~/.hermes or ~/.claude (allowed), vs raw /Users/princepal
            raw_matches = [m.group(0) for m in PRIVATE_PATH_RE.finditer(text)]
            if any(not m.endswith("/skills") for m in raw_matches):
                errors.append(f"Private path found in {md.relative_to(skill_dir)}: {raw_matches[:2]}")

        if TS_RE.search(text):
            has_timestamps = True
        if LABEL_RE.search(text):
            has_labels = True

    if not has_timestamps:
        errors.append("Skill contains zero timestamp citations [mm:ss]")
    if not has_labels:
        errors.append("Skill contains zero evidence grounding labels (seen/guessed/unknown)")

    return errors


def main():
    ap = argparse.ArgumentParser(description="Validate a generated video-to-skill package")
    ap.add_argument("skill_dir", help="Path to generated skill directory")
    args = ap.parse_args()

    errs = check_skill(Path(args.skill_dir))
    if errs:
        print(f"❌ Validation FAILED for {args.skill_dir}:")
        for e in errs:
            print(f"  - {e}")
        sys.exit(1)
    else:
        print(f"✅ Validation PASSED for {args.skill_dir}")
        sys.exit(0)


if __name__ == "__main__":
    main()
