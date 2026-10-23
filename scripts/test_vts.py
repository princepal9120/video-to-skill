#!/usr/bin/env python3
"""Test suite for video-to-skill extractor and validator."""

import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent))

from extract import dedupe_cues, parse_summarize_transcript, parse_vtt
from validate import check_skill


class TestVideoToSkill(unittest.TestCase):
    def test_dedupe_cues(self):
        cues = [
            (0.0, "The number one trending repo"),
            (2.0, "trending repo on GitHub"),
            (4.0, "on GitHub lets Claude reverse engineer"),
        ]
        deduped = dedupe_cues(cues)
        self.assertTrue(len(deduped) >= 1)
        full_text = " ".join(t for _, t in deduped)
        self.assertIn("The number one trending repo on GitHub lets Claude reverse engineer", full_text)

    def test_parse_summarize_transcript(self):
        sample = """Transcript:
[0:00] First point about AI
[0:15] Second point about architecture
and continuation line
"""
        parsed = parse_summarize_transcript(sample)
        self.assertEqual(len(parsed), 2)
        self.assertEqual(parsed[0], (0, "First point about AI"))
        self.assertEqual(parsed[1], (15, "Second point about architecture and continuation line"))

    def test_validate_clean_skill(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            (p / "SKILL.md").write_text("""---
name: sample-skill
description: "Sample test skill"
---
# Sample
- [0:15] [seen] Feature demonstration.
""")
            (p / "timestamps.md").write_text("[0:15] Feature demonstration")
            errs = check_skill(p)
            self.assertEqual(errs, [])

    def test_validate_flags_missing_labels(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            (p / "SKILL.md").write_text("""---
name: sample-skill
description: "Sample test skill"
---
# Sample
- [0:15] Feature demonstration without any evidence label.
""")
            errs = check_skill(p)
            self.assertTrue(any("evidence grounding labels" in e for e in errs))


if __name__ == "__main__":
    unittest.main()
