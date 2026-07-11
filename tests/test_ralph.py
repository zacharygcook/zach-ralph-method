#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import json
import os
import shlex
import subprocess
import sys
import tempfile
import time
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
                "--chunk-validation-command",
                "true",
                "--sprint-validation-command",
                "true",
            )
            second = run_cli(
                "init",
                "--repo",
                str(repo),
                "--agent",
                "codex",
                "--chunk-validation-command",
                "true",
                "--sprint-validation-command",
                "true",
            )
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertIn("remains disarmed", first.stdout)
            self.assertNotEqual(second.returncode, 0)
            config = ralph.parse_config(repo / ".ralph" / "config.env")
            self.assertEqual(config["RALPH_UNATTENDED_APPROVED"], "false")
            self.assertEqual(config["RALPH_AUTO_COMMIT"], "false")
            self.assertEqual(config["RALPH_CHUNK_VALIDATION_COMMAND"], "true")
            self.assertEqual(config["RALPH_SPRINT_VALIDATION_COMMAND"], "true")

    def test_update_runtime_preserves_config_and_sprints(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory) / "repo"
            initialize_repo(repo)
            self.assertEqual(
                run_cli("init", "--repo", str(repo), "--disable-chunk-validation", "--disable-tests").returncode,
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
                "--agent-command", "true", "--chunk-validation-command", "true", "--disable-tests",
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
                "import json, os, pathlib, subprocess\n"
                "prompt = pathlib.Path(os.environ['RALPH_PROMPT_FILE'])\n"
                "chunks = prompt.parent / 'chunks.json'\n"
                "data = json.loads(chunks.read_text())\n"
                "data['chunks'][0]['passes'] = True\n"
                "chunks.write_text(json.dumps(data, indent=2) + '\\n')\n"
                "repo = pathlib.Path(os.environ['RALPH_PROJECT_ROOT']) / 'service'\n"
                "readme = repo / 'README.md'\n"
                "readme.write_text(readme.read_text() + 'chunk complete\\n')\n"
                "subprocess.run(['git', 'add', 'README.md'], cwd=repo, check=True)\n"
                "subprocess.run(['git', 'commit', '-m', 'Complete fixture chunk'], cwd=repo, check=True, capture_output=True)\n"
                "print('RALPH_CHUNK_COMPLETE')\n",
                encoding="utf-8",
            )
            command = f"{shlex.quote(sys.executable)} {shlex.quote(str(fake_agent))}"
            initialized = run_cli(
                "init", "--repo", str(root), "--mode", "multi-repo",
                "--repos", "service", "dashboard", "--agent", "custom",
                "--agent-command", command, "--approve-unattended",
                "--disable-review", "--disable-documentation", "--disable-tests",
                "--chunk-validation-command", "true",
            )
            self.assertEqual(initialized.returncode, 0, initialized.stderr)
            sprint = create_sprint(root, repo="service")
            replace_config(root / ".ralph" / "config.env", "CURRENT_SPRINT", "1-demo")
            replace_config(root / ".ralph" / "config.env", "MAX_ITERATIONS", "2")
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
                run_cli("init", "--repo", str(repo), "--disable-chunk-validation", "--disable-tests").returncode, 0
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
            self.assertEqual(
                run_cli(
                    "init", "--repo", str(repo),
                    "--disable-chunk-validation", "--disable-sprint-validation",
                ).returncode,
                0,
            )
            sprint = create_sprint(repo)
            config = repo / ".ralph" / "config.env"
            replace_config(config, "RALPH_CHUNK_VALIDATION_ENABLED", "true")
            replace_config(config, "RALPH_SPRINT_VALIDATION_ENABLED", "true")
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
            self.assertIn("enabled but RALPH_CHUNK_VALIDATION_COMMAND is empty", details)
            self.assertIn("enabled but RALPH_SPRINT_VALIDATION_COMMAND is empty", details)
            self.assertIn("sprint:1-demo:SCRATCHPAD.md", checks)
            self.assertIn("runtime:fingerprint", checks)

    def test_clean_room_custom_agent_completes_chunks_and_hooks(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory) / "repo with spaces"
            initialize_repo(repo)
            fake_agent = repo / "fake_agent.py"
            fake_agent.write_text(
                "import json, os, pathlib, subprocess\n"
                "prompt = pathlib.Path(os.environ['RALPH_PROMPT_FILE'])\n"
                "chunks = prompt.parent / 'chunks.json'\n"
                "data = json.loads(chunks.read_text())\n"
                "data['chunks'][0]['passes'] = True\n"
                "chunks.write_text(json.dumps(data, indent=2) + '\\n')\n"
                "root = pathlib.Path(os.environ['RALPH_PROJECT_ROOT'])\n"
                "readme = root / 'README.md'\n"
                "readme.write_text(readme.read_text() + 'chunk complete\\n')\n"
                "subprocess.run(['git', 'add', 'README.md', str(chunks.relative_to(root))], cwd=root, check=True)\n"
                "subprocess.run(['git', 'commit', '-m', 'Complete fixture chunk'], cwd=root, check=True, capture_output=True)\n"
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
                "--chunk-validation-command",
                "true",
            )
            self.assertEqual(initialized.returncode, 0, initialized.stderr)
            sprint = create_sprint(repo)
            config = repo / ".ralph" / "config.env"
            replace_config(config, "CURRENT_SPRINT", "1-demo")
            replace_config(config, "MAX_ITERATIONS", "2")
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
            for hook in ("review", "documentation", "validation"):
                self.assertEqual(manifest["hooks"][hook]["status"], "skipped")
                self.assertTrue((sprint / f".hook-{hook}.done").is_file())
            status = run_cli("status", "--repo", str(repo))
            self.assertEqual(status.returncode, 0, status.stderr)
            self.assertIn("Manifest phase: hooks_done", status.stdout)
            self.assertFalse(run("git", "status", "--porcelain", cwd=repo).stdout == "")

    def test_failed_chunk_validation_resets_and_repairs_next_iteration(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory) / "repo"
            initialize_repo(repo)
            validator = repo / "validate.sh"
            validator.write_text(
                "#!/usr/bin/env bash\n"
                "if [[ ! -f .validation-seen ]]; then touch .validation-seen; exit 1; fi\n"
                "exit 0\n",
                encoding="utf-8",
            )
            validator.chmod(0o755)
            fake_agent = repo / "fake_agent.py"
            fake_agent.write_text(
                "import json, os, pathlib, subprocess\n"
                "root = pathlib.Path(os.environ['RALPH_PROJECT_ROOT'])\n"
                "prompt = pathlib.Path(os.environ['RALPH_PROMPT_FILE'])\n"
                "chunks = prompt.parent / 'chunks.json'\n"
                "data = json.loads(chunks.read_text())\n"
                "data['chunks'][0]['passes'] = True\n"
                "chunks.write_text(json.dumps(data, indent=2) + '\\n')\n"
                "readme = root / 'README.md'\n"
                "readme.write_text(readme.read_text() + 'attempt\\n')\n"
                "subprocess.run(['git', 'add', 'README.md', str(chunks.relative_to(root))], cwd=root, check=True)\n"
                "subprocess.run(['git', 'commit', '-m', 'Attempt fixture chunk'], cwd=root, check=True, capture_output=True)\n"
                "print('RALPH_CHUNK_COMPLETE')\n",
                encoding="utf-8",
            )
            command = f"{shlex.quote(sys.executable)} {shlex.quote(str(fake_agent))}"
            initialized = run_cli(
                "init", "--repo", str(repo), "--agent", "custom",
                "--agent-command", command, "--approve-unattended",
                "--chunk-validation-command", "./validate.sh",
                "--disable-review", "--disable-documentation", "--disable-sprint-validation",
            )
            self.assertEqual(initialized.returncode, 0, initialized.stderr)
            sprint = create_sprint(repo)
            config = repo / ".ralph" / "config.env"
            replace_config(config, "CURRENT_SPRINT", "1-demo")
            replace_config(config, "MAX_ITERATIONS", "3")
            loop = run(str(repo / ".ralph" / "loop.sh"), cwd=repo)
            self.assertEqual(loop.returncode, 0, f"{loop.stdout}\n{loop.stderr}")
            manifest = json.loads((sprint / "manifest.json").read_text())
            attempts = manifest["validation"]["chunk_attempts"]
            self.assertEqual([item["status"] for item in attempts], ["failed", "passed"])
            self.assertIn("configured chunk validation failed", (sprint / "SCRATCHPAD.md").read_text())
            self.assertTrue(json.loads((sprint / "chunks.json").read_text())["chunks"][0]["passes"])

    def test_multiple_chunk_transition_is_rejected_without_validation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory) / "repo"
            initialize_repo(repo)
            fake_agent = repo / "fake_agent.py"
            fake_agent.write_text(
                "import json, os, pathlib, subprocess\n"
                "root = pathlib.Path(os.environ['RALPH_PROJECT_ROOT'])\n"
                "prompt = pathlib.Path(os.environ['RALPH_PROMPT_FILE'])\n"
                "chunks = prompt.parent / 'chunks.json'\n"
                "data = json.loads(chunks.read_text())\n"
                "data['chunks'][0]['passes'] = data['chunks'][1]['passes'] = True\n"
                "chunks.write_text(json.dumps(data, indent=2) + '\\n')\n"
                "subprocess.run(['git', 'add', str(chunks.relative_to(root))], cwd=root, check=True)\n"
                "subprocess.run(['git', 'commit', '-m', 'Claim two chunks'], cwd=root, check=True, capture_output=True)\n"
                "print('RALPH_CHUNK_COMPLETE')\n",
                encoding="utf-8",
            )
            command = f"{shlex.quote(sys.executable)} {shlex.quote(str(fake_agent))}"
            initialized = run_cli(
                "init", "--repo", str(repo), "--agent", "custom", "--agent-command", command,
                "--approve-unattended", "--chunk-validation-command", "true",
                "--disable-review", "--disable-documentation", "--disable-sprint-validation",
            )
            self.assertEqual(initialized.returncode, 0, initialized.stderr)
            sprint = create_sprint(repo)
            chunks_path = sprint / "chunks.json"
            payload = json.loads(chunks_path.read_text())
            payload["chunks"].append({
                "id": 2, "title": "Second", "passes": False,
                "acceptance_criteria": ["Second completes"], "artifacts": ["README.md"],
            })
            chunks_path.write_text(json.dumps(payload, indent=2) + "\n")
            config = repo / ".ralph" / "config.env"
            replace_config(config, "CURRENT_SPRINT", "1-demo")
            replace_config(config, "MAX_ITERATIONS", "1")
            loop = run(str(repo / ".ralph" / "loop.sh"), cwd=repo)
            self.assertEqual(loop.returncode, 2, loop.stdout)
            chunks = json.loads(chunks_path.read_text())["chunks"]
            self.assertEqual([chunk["passes"] for chunk in chunks], [False, False])
            manifest = json.loads((sprint / "manifest.json").read_text())
            self.assertEqual(manifest["validation"]["chunk_attempts"], [])

    def test_failed_sprint_validation_is_resumable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory) / "repo"
            initialize_repo(repo)
            sprint_validator = repo / "sprint_validate.sh"
            sprint_validator.write_text("#!/usr/bin/env bash\nexit 1\n", encoding="utf-8")
            sprint_validator.chmod(0o755)
            fake_agent = repo / "fake_agent.py"
            fake_agent.write_text(
                "import json, os, pathlib, subprocess\n"
                "root = pathlib.Path(os.environ['RALPH_PROJECT_ROOT'])\n"
                "prompt = pathlib.Path(os.environ['RALPH_PROMPT_FILE'])\n"
                "chunks = prompt.parent / 'chunks.json'\n"
                "data = json.loads(chunks.read_text())\n"
                "data['chunks'][0]['passes'] = True\n"
                "chunks.write_text(json.dumps(data, indent=2) + '\\n')\n"
                "readme = root / 'README.md'\n"
                "readme.write_text(readme.read_text() + 'complete\\n')\n"
                "subprocess.run(['git', 'add', 'README.md', str(chunks.relative_to(root))], cwd=root, check=True)\n"
                "subprocess.run(['git', 'commit', '-m', 'Complete chunk'], cwd=root, check=True, capture_output=True)\n"
                "print('RALPH_CHUNK_COMPLETE')\n",
                encoding="utf-8",
            )
            command = f"{shlex.quote(sys.executable)} {shlex.quote(str(fake_agent))}"
            initialized = run_cli(
                "init", "--repo", str(repo), "--agent", "custom", "--agent-command", command,
                "--approve-unattended", "--chunk-validation-command", "true",
                "--sprint-validation-command", "./sprint_validate.sh",
                "--disable-review", "--disable-documentation",
            )
            self.assertEqual(initialized.returncode, 0, initialized.stderr)
            sprint = create_sprint(repo)
            config = repo / ".ralph" / "config.env"
            replace_config(config, "CURRENT_SPRINT", "1-demo")
            first = run(str(repo / ".ralph" / "loop.sh"), cwd=repo)
            self.assertEqual(first.returncode, 14, first.stdout)
            manifest = json.loads((sprint / "manifest.json").read_text())
            self.assertEqual(manifest["phase"], "chunks_done")
            self.assertEqual(manifest["hooks"]["validation"]["status"], "failed")

            sprint_validator.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
            second = run(str(repo / ".ralph" / "loop.sh"), cwd=repo)
            self.assertEqual(second.returncode, 0, second.stdout)
            manifest = json.loads((sprint / "manifest.json").read_text())
            self.assertEqual(manifest["phase"], "hooks_done")
            self.assertEqual(manifest["hooks"]["validation"]["status"], "done")

    def test_interrupted_chunk_validation_resets_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory) / "repo"
            initialize_repo(repo)
            fake_agent = repo / "fake_agent.py"
            fake_agent.write_text(
                "import json, os, pathlib, subprocess\n"
                "root = pathlib.Path(os.environ['RALPH_PROJECT_ROOT'])\n"
                "prompt = pathlib.Path(os.environ['RALPH_PROMPT_FILE'])\n"
                "chunks = prompt.parent / 'chunks.json'\n"
                "data = json.loads(chunks.read_text())\n"
                "data['chunks'][0]['passes'] = True\n"
                "chunks.write_text(json.dumps(data, indent=2) + '\\n')\n"
                "readme = root / 'README.md'\n"
                "readme.write_text(readme.read_text() + 'candidate\\n')\n"
                "subprocess.run(['git', 'add', 'README.md', str(chunks.relative_to(root))], cwd=root, check=True)\n"
                "subprocess.run(['git', 'commit', '-m', 'Create candidate'], cwd=root, check=True, capture_output=True)\n"
                "print('RALPH_CHUNK_COMPLETE')\n",
                encoding="utf-8",
            )
            command = f"{shlex.quote(sys.executable)} {shlex.quote(str(fake_agent))}"
            initialized = run_cli(
                "init", "--repo", str(repo), "--agent", "custom", "--agent-command", command,
                "--approve-unattended", "--chunk-validation-command", "sleep 30",
                "--disable-review", "--disable-documentation", "--disable-sprint-validation",
            )
            self.assertEqual(initialized.returncode, 0, initialized.stderr)
            sprint = create_sprint(repo)
            replace_config(repo / ".ralph" / "config.env", "CURRENT_SPRINT", "1-demo")
            process = subprocess.Popen(
                [str(repo / ".ralph" / "loop.sh")], cwd=repo,
                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
            )
            validation_logs: list[Path] = []
            for _attempt in range(100):
                validation_logs = list((repo / ".ralph" / "logs").glob("**/chunk-1-validation-1.log"))
                if validation_logs:
                    break
                time.sleep(0.1)
            self.assertTrue(validation_logs, "validation did not start")
            process.terminate()
            output, _ = process.communicate(timeout=10)
            self.assertEqual(process.returncode, 143, output)
            self.assertFalse(json.loads((sprint / "chunks.json").read_text())["chunks"][0]["passes"])
            manifest = json.loads((sprint / "manifest.json").read_text())
            self.assertEqual(manifest["validation"]["chunk_attempts"][-1]["status"], "interrupted")

    def test_loop_refuses_without_explicit_unattended_approval(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory) / "repo"
            initialize_repo(repo)
            self.assertEqual(
                run_cli("init", "--repo", str(repo), "--disable-chunk-validation", "--disable-tests").returncode, 0
            )
            create_sprint(repo)
            replace_config(repo / ".ralph" / "config.env", "CURRENT_SPRINT", "1-demo")
            result = run(str(repo / ".ralph" / "loop.sh"), cwd=repo)
            self.assertEqual(result.returncode, 14)
            self.assertIn("Refusing autonomous execution", result.stdout)


if __name__ == "__main__":
    unittest.main()
