#!/usr/bin/env python3

from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class DocumentationContractTest(unittest.TestCase):
    def test_readme_prioritizes_skills_cli_before_runtime_commands(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        add = "npx skills@latest add"
        update = "npx skills@latest update"
        restore = "npx skills@latest experimental_install"
        runtime = "python3 .agents/skills/ralph-workflows/scripts/ralph.py"
        for command in (add, update, restore, runtime):
            self.assertIn(command, readme)
        self.assertLess(readme.index(add), readme.index(runtime))
        self.assertIn("What `npx skills` manages", readme)

    def test_quick_start_is_an_actionable_operator_journey(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        quick_start = readme.split("## Quick start", 1)[1].split(
            "## Supported agent harnesses", 1
        )[0]
        for prerequisite in ("Python 3", "jq", "SPEC.md", "validation command"):
            self.assertIn(prerequisite, quick_start)
        self.assertIn("Use $ralph-workflows to preflight", quick_start)
        self.assertIn("You do **not** manually create `.ralph/`", quick_start)
        self.assertIn("exact model", quick_start)
        self.assertIn("maximum sprint turns", quick_start)
        self.assertIn("maximum turns per chunk", quick_start)
        self.assertIn("./.ralph/loop.sh", quick_start)
        self.assertIn("Which workflow should I ask for?", quick_start)

    def test_skill_explains_package_and_runtime_boundary(self) -> None:
        skill = (ROOT / "skill" / "SKILL.md").read_text(encoding="utf-8")
        normalized = " ".join(skill.split())
        self.assertIn("npx skills@latest update ralph-workflows", skill)
        self.assertIn("does not run arbitrary lifecycle hooks", normalized)
        self.assertIn("Do not ask the operator to hand-build `.ralph/`", skill)
        self.assertTrue((ROOT / "skill" / "references" / "first-run.md").is_file())


if __name__ == "__main__":
    unittest.main()
