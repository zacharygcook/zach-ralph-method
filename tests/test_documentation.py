#!/usr/bin/env python3

from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class DocumentationContractTest(unittest.TestCase):
    def test_readme_prioritizes_skills_cli_before_runtime_commands(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        add = "npx zacharygcook/zach-ralph-method"
        restore = "npx skills experimental_install"
        runtime = "./.agents/skills/ralph-workflows/scripts/ralph"
        for command in (add, restore, runtime):
            self.assertIn(command, readme)
        self.assertLess(readme.index(add), readme.index(runtime))
        self.assertNotIn(" --copy -y", readme)
        self.assertNotIn(" --project -y", readme)
        human = readme.split("## Automation interface", 1)[0]
        automation = readme.split("## Automation interface", 1)[1]
        self.assertIn("just init", human)
        self.assertIn("just upgrade", human)
        self.assertNotIn("/scripts/ralph init", human)
        self.assertNotIn("@latest", human)
        self.assertNotIn("--skill ralph-workflows", human)
        self.assertNotIn("cp -n", human)
        self.assertIn("/scripts/ralph init", automation)

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
        self.assertIn("just run", quick_start)
        self.assertIn("Which workflow should I ask for?", quick_start)

    def test_skill_explains_package_and_runtime_boundary(self) -> None:
        skill = (ROOT / "skill" / "SKILL.md").read_text(encoding="utf-8")
        normalized = " ".join(skill.split())
        self.assertIn("just upgrade", skill)
        self.assertIn("does not run arbitrary lifecycle hooks", normalized)
        self.assertIn("Do not ask the operator to hand-build `.ralph/`", skill)
        self.assertTrue((ROOT / "skill" / "references" / "first-run.md").is_file())
        self.assertTrue((ROOT / "skill" / "justfile").is_file())
        self.assertTrue((ROOT / "skill" / "recipes.just").is_file())


if __name__ == "__main__":
    unittest.main()
