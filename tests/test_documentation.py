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
        runtime = "./.agents/skills/ralph-loop/scripts/ralph"
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
        self.assertIn("Use $ralph-loop to set up a Ralph loop", quick_start)
        self.assertIn("You do **not** manually create `.ralph/`", quick_start)
        self.assertIn("required runtime choices", quick_start)
        self.assertIn("review before starting the loop", quick_start)
        self.assertIn("just run", quick_start)
        self.assertIn("Which skill should I use?", quick_start)
        for name in ("$ralph-loop", "$ralph-sprint", "$ralph-status", "$ralph-review"):
            self.assertIn(name, quick_start)

    def test_skill_explains_package_and_runtime_boundary(self) -> None:
        skill_root = ROOT / "skills" / "ralph-loop"
        skill = (skill_root / "SKILL.md").read_text(encoding="utf-8")
        normalized = " ".join(skill.split())
        self.assertIn("just upgrade", skill)
        self.assertIn("does not run arbitrary lifecycle hooks", normalized)
        self.assertIn("Do not ask the operator to hand-build `.ralph/`", skill)
        self.assertTrue((skill_root / "references" / "first-run.md").is_file())
        self.assertTrue((skill_root / "justfile").is_file())
        self.assertTrue((skill_root / "recipes.just").is_file())

    def test_repository_exposes_four_focused_skills(self) -> None:
        for name in ("ralph-loop", "ralph-sprint", "ralph-status", "ralph-review"):
            root = ROOT / "skills" / name
            self.assertTrue((root / "SKILL.md").is_file())
            self.assertTrue((root / "agents" / "openai.yaml").is_file())
            self.assertTrue((root / "skill-package.json").is_file())


if __name__ == "__main__":
    unittest.main()
