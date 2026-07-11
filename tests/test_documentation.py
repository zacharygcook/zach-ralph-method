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

    def test_skill_explains_package_and_runtime_boundary(self) -> None:
        skill = (ROOT / "skill" / "SKILL.md").read_text(encoding="utf-8")
        normalized = " ".join(skill.split())
        self.assertIn("npx skills@latest update ralph-workflows", skill)
        self.assertIn("does not run arbitrary lifecycle hooks", normalized)


if __name__ == "__main__":
    unittest.main()
