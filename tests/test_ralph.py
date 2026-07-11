#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import json
import os
import shlex
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "ralph.py"
SPEC = importlib.util.spec_from_file_location("ralph", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Unable to load ralph.py")
ralph = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = ralph
SPEC.loader.exec_module(ralph)


def run(
    *arguments: str, cwd: Path | None = None, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    environment = dict(os.environ)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    if env:
        environment.update(env)
    return subprocess.run(
        arguments, cwd=cwd, env=environment, check=False, capture_output=True, text=True
    )


def run_cli(*arguments: str) -> subprocess.CompletedProcess[str]:
    return run(sys.executable, str(MODULE_PATH), *arguments)


def initialize_repo(path: Path) -> None:
    path.mkdir()
    (path / "README.md").write_text("# Fixture\n", encoding="utf-8")
    for command in (
        ("git", "init", "-b", "master"),
        ("git", "config", "user.name", "Ralph Test"),
        ("git", "config", "user.email", "ralph@example.com"),
        ("git", "add", "README.md"),
        ("git", "commit", "-m", "Create fixture"),
    ):
        result = run(*command, cwd=path)
        if result.returncode != 0:
            raise RuntimeError(result.stderr)


def replace_config(path: Path, key: str, value: str) -> None:
    lines = path.read_text(encoding="utf-8").splitlines()
    found = False
    output: list[str] = []
    for line in lines:
        if line.startswith(f"{key}="):
            output.append(f"{key}={value}")
            found = True
        else:
            output.append(line)
    if not found:
        output.append(f"{key}={value}")
    path.write_text("\n".join(output) + "\n", encoding="utf-8")


def create_sprint(root: Path, name: str = "1-demo", repo: str | None = None) -> Path:
    sprint = root / ".ralph" / "sprints" / name
    sprint.mkdir(parents=True)
    for filename in (
        "README.md",
        "IMPLEMENTATION_PLAN.md",
        "relevant-specs.md",
        "SCRATCHPAD.md",
    ):
        (sprint / filename).write_text(f"# {filename}\n", encoding="utf-8")
    (sprint / "prompt.md").write_text(
        "Read SCRATCHPAD.md first. Update chunks.json and emit RALPH_CHUNK_COMPLETE.\n",
        encoding="utf-8",
    )
    chunk = {
        "id": 1,
        "title": "Complete fixture",
        "passes": False,
        "acceptance_criteria": ["Fixture becomes complete"],
        "artifacts": ["README.md"],
    }
    if repo:
        chunk["repo"] = repo
    (sprint / "chunks.json").write_text(
        json.dumps(
            {
                "chunks": [
                    chunk
                ]
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return sprint


class RalphRuntimeTest(unittest.TestCase):
    def test_recovered_shell_runtime_has_valid_syntax(self) -> None:
        scripts = sorted(
            {
                path
                for mode in ralph.MODES
                for relative, path in ralph.runtime_sources(mode).items()
                if relative.endswith(".sh")
            }
        )
        result = run("bash", "-n", *(str(path) for path in scripts))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertGreaterEqual(len(scripts), 7)

    def test_init_is_disarmed_and_refuses_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory) / "repo with spaces"
            initialize_repo(repo)
            first = run_cli(
                "init",
                "--repo",
                str(repo),
                "--agent",
                "codex",
                "--test-command",
                "true",
            )
            second = run_cli(
                "init",
                "--repo",
                str(repo),
                "--agent",
                "codex",
                "--test-command",
                "true",
            )
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertIn("remains disarmed", first.stdout)
            self.assertNotEqual(second.returncode, 0)
            config = ralph.parse_config(repo / ".ralph" / "config.env")
            self.assertEqual(config["RALPH_UNATTENDED_APPROVED"], "false")
            self.assertEqual(config["RALPH_AUTO_COMMIT"], "false")
            self.assertEqual(config["RALPH_TEST_COMMAND"], "true")

    def test_update_runtime_preserves_config_and_sprints(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory) / "repo"
            initialize_repo(repo)
            self.assertEqual(
                run_cli("init", "--repo", str(repo), "--disable-tests").returncode,
                0,
            )
            sprint = create_sprint(repo)
            config = repo / ".ralph" / "config.env"
            replace_config(config, "CURRENT_SPRINT", "1-demo")
            loop = repo / ".ralph" / "loop.sh"
            loop.write_text("tampered\n", encoding="utf-8")
            result = run_cli("init", "--repo", str(repo), "--update-runtime")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("CURRENT_SPRINT=1-demo", config.read_text(encoding="utf-8"))
            self.assertTrue((sprint / "SCRATCHPAD.md").is_file())
            self.assertEqual(
                ralph.sha256(loop), ralph.sha256(ralph.runtime_sources("monorepo")["loop.sh"])
            )

    def test_multi_repo_init_and_validation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "project with spaces"
            root.mkdir()
            initialize_repo(root / "api")
            initialize_repo(root / "web")
            result = run_cli(
                "init", "--repo", str(root), "--mode", "multi-repo",
                "--repos", "api", "web", "--agent", "custom",
                "--agent-command", "true", "--disable-tests",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            create_sprint(root, repo="api")
            replace_config(root / ".ralph" / "config.env", "CURRENT_SPRINT", "1-demo")
            report = run_cli("validate", "--repo", str(root), "--json")
            self.assertEqual(report.returncode, 0, report.stdout)
            metadata = json.loads((root / ".ralph" / ".runtime-manifest.json").read_text())
            self.assertEqual(metadata["mode"], "multi-repo")
            self.assertEqual(metadata["repositories"], ["api", "web"])

    def test_clean_room_multi_repo_loop_tracks_each_repository(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "project"
            root.mkdir()
            initialize_repo(root / "service")
            initialize_repo(root / "dashboard")
            fake_agent = root / "fake_agent.py"
            fake_agent.write_text(
                "import json, os, pathlib\n"
                "prompt = pathlib.Path(os.environ['RALPH_PROMPT_FILE'])\n"
                "chunks = prompt.parent / 'chunks.json'\n"
                "data = json.loads(chunks.read_text())\n"
                "data['chunks'][0]['passes'] = True\n"
                "chunks.write_text(json.dumps(data, indent=2) + '\\n')\n"
                "print('RALPH_CHUNK_COMPLETE')\n",
                encoding="utf-8",
            )
            command = f"{shlex.quote(sys.executable)} {shlex.quote(str(fake_agent))}"
            initialized = run_cli(
                "init", "--repo", str(root), "--mode", "multi-repo",
                "--repos", "service", "dashboard", "--agent", "custom",
                "--agent-command", command, "--approve-unattended",
                "--disable-review", "--disable-documentation", "--disable-tests",
            )
            self.assertEqual(initialized.returncode, 0, initialized.stderr)
            sprint = create_sprint(root, repo="service")
            replace_config(root / ".ralph" / "config.env", "CURRENT_SPRINT", "1-demo")
            loop = run(str(root / ".ralph" / "loop.sh"), cwd=root)
            self.assertEqual(loop.returncode, 0, f"{loop.stdout}\n{loop.stderr}")
            manifest = json.loads((sprint / "manifest.json").read_text())
            self.assertEqual(manifest["phase"], "hooks_done")
            self.assertEqual(set(manifest["repos"]), {"service", "dashboard"})
            for repo in ("service", "dashboard"):
                self.assertTrue(manifest["repos"][repo]["start_commit"])
                self.assertTrue(manifest["repos"][repo]["end_commit"])

    def test_update_refuses_managed_symlink_without_partial_write(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo = root / "repo"
            initialize_repo(repo)
            self.assertEqual(
                run_cli("init", "--repo", str(repo), "--disable-tests").returncode, 0
            )
            loop = repo / ".ralph" / "loop.sh"
            loop.write_text("keep this local drift\n", encoding="utf-8")
            outside = root / "outside.sh"
            outside.write_text("outside\n", encoding="utf-8")
            review = repo / ".ralph" / "hooks" / "review.sh"
            review.unlink()
            review.symlink_to(outside)
            result = run_cli("init", "--repo", str(repo), "--update-runtime")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Refusing to replace managed symlink", result.stderr)
            self.assertEqual(
                loop.read_text(encoding="utf-8"), "keep this local drift\n"
            )
            self.assertEqual(outside.read_text(encoding="utf-8"), "outside\n")

    def test_validate_reports_configuration_and_sprint_defects(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory) / "repo"
            initialize_repo(repo)
            self.assertEqual(run_cli("init", "--repo", str(repo)).returncode, 0)
            sprint = create_sprint(repo)
            (sprint / "SCRATCHPAD.md").unlink()
            with (repo / ".ralph" / "status.sh").open("a", encoding="utf-8") as handle:
                handle.write("# drift\n")
            result = run_cli("validate", "--repo", str(repo), "--json")
            report = json.loads(result.stdout)
            self.assertNotEqual(result.returncode, 0)
            details = "\n".join(item["detail"] for item in report["findings"])
            checks = {
                item["check"] for item in report["findings"] if item["status"] == "fail"
            }
            self.assertIn("enabled but RALPH_TEST_COMMAND is empty", details)
            self.assertIn("sprint:1-demo:SCRATCHPAD.md", checks)
            self.assertIn("runtime:fingerprint", checks)

    def test_clean_room_custom_agent_completes_chunks_and_hooks(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory) / "repo with spaces"
            initialize_repo(repo)
            fake_agent = repo / "fake_agent.py"
            fake_agent.write_text(
                "import json, os, pathlib\n"
                "prompt = pathlib.Path(os.environ['RALPH_PROMPT_FILE'])\n"
                "chunks = prompt.parent / 'chunks.json'\n"
                "data = json.loads(chunks.read_text())\n"
                "data['chunks'][0]['passes'] = True\n"
                "chunks.write_text(json.dumps(data, indent=2) + '\\n')\n"
                "print('RALPH_CHUNK_COMPLETE')\n",
                encoding="utf-8",
            )
            command = f"{shlex.quote(sys.executable)} {shlex.quote(str(fake_agent))}"
            initialized = run_cli(
                "init",
                "--repo",
                str(repo),
                "--agent",
                "custom",
                "--agent-command",
                command,
                "--approve-unattended",
                "--disable-review",
                "--disable-documentation",
                "--disable-tests",
            )
            self.assertEqual(initialized.returncode, 0, initialized.stderr)
            sprint = create_sprint(repo)
            config = repo / ".ralph" / "config.env"
            replace_config(config, "CURRENT_SPRINT", "1-demo")
            validated = run_cli("validate", "--repo", str(repo), "--json")
            self.assertEqual(validated.returncode, 0, validated.stdout)
            loop = run(str(repo / ".ralph" / "loop.sh"), cwd=repo)
            self.assertEqual(loop.returncode, 0, f"{loop.stdout}\n{loop.stderr}")
            manifest = json.loads(
                (sprint / "manifest.json").read_text(encoding="utf-8")
            )
            self.assertEqual(manifest["phase"], "hooks_done")
            self.assertTrue(
                json.loads((sprint / "chunks.json").read_text())["chunks"][0]["passes"]
            )
            for hook in ("review", "documentation", "tests"):
                self.assertEqual(manifest["hooks"][hook]["status"], "skipped")
                self.assertTrue((sprint / f".hook-{hook}.done").is_file())
            status = run_cli("status", "--repo", str(repo))
            self.assertEqual(status.returncode, 0, status.stderr)
            self.assertIn("Manifest phase: hooks_done", status.stdout)
            self.assertFalse(run("git", "status", "--porcelain", cwd=repo).stdout == "")

    def test_loop_refuses_without_explicit_unattended_approval(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory) / "repo"
            initialize_repo(repo)
            self.assertEqual(
                run_cli("init", "--repo", str(repo), "--disable-tests").returncode, 0
            )
            create_sprint(repo)
            replace_config(repo / ".ralph" / "config.env", "CURRENT_SPRINT", "1-demo")
            result = run(str(repo / ".ralph" / "loop.sh"), cwd=repo)
            self.assertEqual(result.returncode, 14)
            self.assertIn("Refusing autonomous execution", result.stdout)


if __name__ == "__main__":
    unittest.main()
