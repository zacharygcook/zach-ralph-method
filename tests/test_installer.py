#!/usr/bin/env python3

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "bin" / "install.mjs"
IMPORT_LINE = "import '.agents/skills/ralph-workflows/recipes.just'"


class InstallerTest(unittest.TestCase):
    def test_npm_bootstrap_version_matches_runtime_release(self) -> None:
        package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
        version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
        self.assertEqual(package["version"], version)
        self.assertEqual(package["files"], ["bin/install.mjs"])

    def test_installer_stops_cleanly_when_just_is_missing(self) -> None:
        node = shutil.which("node")
        self.assertIsNotNone(node)
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run(
                [str(node), str(INSTALLER)],
                cwd=directory,
                env={**os.environ, "PATH": directory},
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 12)
            self.assertIn("Install just first", result.stderr)

    def run_installer(self, repo: Path) -> subprocess.CompletedProcess[str]:
        node = shutil.which("node")
        self.assertIsNotNone(node)
        fake_bin = repo / "fake-bin"
        fake_bin.mkdir(exist_ok=True)
        capture = repo / "npx-arguments.txt"
        fake_npx = fake_bin / "npx"
        fake_npx.write_text(
            "#!/usr/bin/env bash\n"
            'printf "%s\\n" "$@" > "$CAPTURE"\n'
            "mkdir -p .agents/skills/ralph-workflows\n",
            encoding="utf-8",
        )
        fake_npx.chmod(0o755)
        fake_just = fake_bin / "just"
        fake_just.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
        fake_just.chmod(0o755)
        return subprocess.run(
            [str(node), str(INSTALLER)],
            cwd=repo,
            env={
                **os.environ,
                "PATH": f"{fake_bin}{os.pathsep}{os.environ['PATH']}",
                "CAPTURE": str(capture),
            },
            check=False,
            capture_output=True,
            text=True,
        )

    def test_installer_uses_bare_skill_command_and_creates_import(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            result = self.run_installer(repo)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(
                (repo / "npx-arguments.txt").read_text(encoding="utf-8").splitlines(),
                ["skills", "add", "zacharygcook/zach-ralph-method"],
            )
            self.assertEqual(
                (repo / "justfile").read_text(encoding="utf-8"),
                IMPORT_LINE + "\n",
            )
            self.assertIn("Run: just init", result.stdout)

    def test_installer_preserves_existing_justfile_and_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            justfile = repo / "Justfile"
            justfile.write_text("test:\n    echo test\n", encoding="utf-8")
            first = self.run_installer(repo)
            second = self.run_installer(repo)
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(second.returncode, 0, second.stderr)
            text = justfile.read_text(encoding="utf-8")
            self.assertIn("test:\n    echo test\n", text)
            self.assertEqual(text.count(IMPORT_LINE), 1)
            self.assertNotIn("justfile", {path.name for path in repo.iterdir()})


if __name__ == "__main__":
    unittest.main()
