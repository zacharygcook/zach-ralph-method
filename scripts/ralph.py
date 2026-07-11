#!/usr/bin/env python3
"""Install, validate, and inspect the hardened Ralph runtime."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
PACKAGE_LAYOUT = (ROOT / "assets" / "templates").is_dir()
TEMPLATES = ROOT / "assets" / "templates" if PACKAGE_LAYOUT else ROOT / "templates"
VERSION_FILE = ROOT / "assets" / "VERSION" if PACKAGE_LAYOUT else ROOT / "VERSION"
SHARED_FILES = {
    "VERSION": VERSION_FILE,
    "format-codex-stream.py": TEMPLATES / "shared" / "format-codex-stream.py",
    "format-stream.py": TEMPLATES / "shared" / "format-stream.py",
    "pretty-process-snapshots.py": TEMPLATES / "shared" / "pretty-process-snapshots.py",
    "lib/ralph-common.sh": TEMPLATES / "shared" / "ralph-common.sh.template",
}
MODE_FILES = {
    "loop.sh": "loop.sh.template",
    "status.sh": "status.sh.template",
    "prompt.md.template": "prompt.md.template",
    "hooks/post-sprint.sh": "hooks/post-sprint.sh.template",
    "hooks/review.sh": "hooks/review.sh.template",
    "hooks/document.sh": "hooks/document.sh.template",
    "hooks/test.sh": "hooks/test.sh.template",
    "prompts/review.md": "prompts/review.md.template",
    "prompts/document.md": "prompts/document.md.template",
    "prompts/test.md": "prompts/test.md.template",
}
MODES = {"monorepo", "multi-repo"}
AGENTS = {"amp", "claude", "codex", "droid", "opencode", "custom"}


class RalphError(ValueError):
    pass


def prompt_choice(label: str, choices: set[str]) -> str:
    ordered = ", ".join(sorted(choices))
    while True:
        value = input(f"{label} ({ordered}): ").strip()
        if value in choices:
            return value
        print(f"Choose one of: {ordered}", file=sys.stderr)


def prompt_positive_integer(label: str) -> int:
    while True:
        value = input(f"{label}: ").strip()
        if value.isdigit() and int(value) > 0:
            return int(value)
        print("Enter a positive integer.", file=sys.stderr)


def resolve_init_operator_choices(arguments: argparse.Namespace) -> None:
    """Collect missing operator intent interactively or fail clearly in automation."""
    missing = []
    if not arguments.agent:
        missing.append("--agent")
    if arguments.agent != "custom" and not arguments.model:
        missing.append("--model")
    if arguments.max_sprint_iterations is None:
        missing.append("--max-sprint-iterations")
    if arguments.max_chunk_iterations is None:
        missing.append("--max-chunk-iterations")
    if not missing:
        return
    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        raise RalphError(
            "Missing operator choices for noninteractive init: " + ", ".join(missing)
        )
    print("Configure Ralph operator controls. No choices are assumed.")
    if not arguments.agent:
        arguments.agent = prompt_choice("Agent harness", AGENTS)
    if arguments.agent != "custom" and not arguments.model:
        arguments.model = input("Exact model: ").strip()
        if not arguments.model:
            raise RalphError("An explicit model is required for a standard harness")
    if arguments.max_sprint_iterations is None:
        arguments.max_sprint_iterations = prompt_positive_integer(
            "Maximum agent turns for the sprint"
        )
    if arguments.max_chunk_iterations is None:
        arguments.max_chunk_iterations = prompt_positive_integer(
            "Maximum agent turns per chunk"
        )


def resolve_upgrade_operator_choices(
    agent: str,
    model: str,
    max_sprint_iterations: int | str | None,
    max_chunk_iterations: int | str | None,
) -> tuple[str, str, int | str, int | str]:
    """Repair incomplete stored operator intent without inventing values."""
    missing = []
    if agent not in AGENTS:
        missing.append("--agent")
    if agent != "custom" and not model:
        missing.append("--model")
    if max_sprint_iterations is None or str(max_sprint_iterations) == "":
        missing.append("--max-sprint-iterations")
    if max_chunk_iterations is None or str(max_chunk_iterations) == "":
        missing.append("--max-chunk-iterations")
    if not missing:
        return agent, model, max_sprint_iterations, max_chunk_iterations
    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        raise RalphError("Missing operator choices for upgrade: " + ", ".join(missing))
    print("Configure missing Ralph operator controls. No choices are assumed.")
    if agent not in AGENTS:
        agent = prompt_choice("Agent harness", AGENTS)
    if agent != "custom" and not model:
        model = input("Exact model: ").strip()
        if not model:
            raise RalphError("An explicit model is required for a standard harness")
    if max_sprint_iterations is None or str(max_sprint_iterations) == "":
        max_sprint_iterations = prompt_positive_integer(
            "Maximum agent turns for the sprint"
        )
    if max_chunk_iterations is None or str(max_chunk_iterations) == "":
        max_chunk_iterations = prompt_positive_integer(
            "Maximum agent turns per chunk"
        )
    return agent, model, max_sprint_iterations, max_chunk_iterations


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def runtime_version() -> str:
    return VERSION_FILE.read_text(encoding="utf-8").strip()


def runtime_sources(mode: str) -> dict[str, Path]:
    if mode not in MODES:
        raise RalphError(f"Unsupported mode: {mode}")
    mode_root = TEMPLATES / mode
    return {
        **SHARED_FILES,
        **{destination: mode_root / source for destination, source in MODE_FILES.items()},
    }


def shell_value(value: str) -> str:
    if not value:
        return ""
    return "'" + value.replace("'", "'\"'\"'") + "'"


def render_config(arguments: argparse.Namespace) -> str:
    values: dict[str, str] = {}
    template = TEMPLATES / arguments.mode / "config.env.template"
    for raw in template.read_text(encoding="utf-8").splitlines():
        if raw and not raw.startswith("#") and "=" in raw:
            key, value = raw.split("=", 1)
            values[key] = value
    values.update(
        {
            "RALPH_AGENT": arguments.agent,
            "RALPH_AGENT_MODEL": shell_value(arguments.model or ""),
            "RALPH_AGENT_COMMAND": shell_value(arguments.agent_command or ""),
            "MAX_SPRINT_ITERATIONS": str(arguments.max_sprint_iterations),
            "MAX_CHUNK_ITERATIONS": str(arguments.max_chunk_iterations),
            "RALPH_CHUNK_VALIDATION_COMMAND": shell_value(
                arguments.chunk_validation_command or ""
            ),
            "RALPH_SPRINT_VALIDATION_COMMAND": shell_value(
                arguments.sprint_validation_command or arguments.test_command or ""
            ),
            "RALPH_E2E_COMMAND": shell_value(arguments.e2e_command or ""),
            "RALPH_REVIEW_ENABLED": "false" if arguments.disable_review else "true",
            "RALPH_DOCUMENTATION_ENABLED": "false"
            if arguments.disable_documentation
            else "true",
            "RALPH_CHUNK_VALIDATION_ENABLED": "false"
            if arguments.disable_chunk_validation
            else "true",
            "RALPH_SPRINT_VALIDATION_ENABLED": "false"
            if arguments.disable_sprint_validation or arguments.disable_tests
            else "true",
            "RALPH_MODE": arguments.mode,
        }
    )
    if arguments.mode == "multi-repo":
        values["RALPH_REPOS"] = shell_value(" ".join(arguments.repos))
        values["RALPH_PRIMARY_REPO"] = arguments.primary_repo or arguments.repos[0]
    lines = [
        "# Generated by the ralph-workflows skill. This file is sourced by Bash; treat it as trusted code."
    ]
    lines.extend(f"{key}={value}" for key, value in values.items())
    return "\n".join(lines) + "\n"


def copy_runtime(target: Path, mode: str) -> dict[str, str]:
    checksums: dict[str, str] = {}
    sources = runtime_sources(mode)
    resolved_target = target.resolve()
    for relative in sources:
        destination = target / relative
        if destination.is_symlink():
            raise RalphError(f"Refusing to replace managed symlink: {destination}")
        if not destination.parent.resolve().is_relative_to(resolved_target):
            raise RalphError(f"Refusing managed path outside runtime: {destination}")
    for relative, source in sources.items():
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        checksums[relative] = sha256(destination)
    return checksums


def write_json(path: Path, value: dict[str, Any]) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    temporary.replace(path)


def install(arguments: argparse.Namespace) -> Path:
    repo = arguments.repo.resolve()
    if arguments.mode == "monorepo" and not (repo / ".git").exists():
        raise RalphError(f"Not a Git repository root: {repo}")
    if arguments.mode == "multi-repo":
        if len(arguments.repos) < 2:
            raise RalphError("Multi-repo mode requires at least two --repos entries")
        missing = [name for name in arguments.repos if not (repo / name / ".git").exists()]
        if missing:
            raise RalphError("Missing child Git repositories: " + ", ".join(missing))
    target = repo / ".ralph"
    config = target / "config.env"
    metadata_path = target / ".runtime-manifest.json"
    if target.is_symlink():
        raise RalphError(f"Refusing symlinked runtime directory: {target}")
    if target.exists():
        return upgrade(arguments)
    resolve_init_operator_choices(arguments)
    if arguments.agent != "custom" and not arguments.model:
        raise RalphError("New runtimes require --model for the selected agent harness")
    if arguments.max_sprint_iterations < 1 or arguments.max_chunk_iterations < 1:
        raise RalphError("Iteration budgets must be positive integers")
    if not arguments.disable_chunk_validation and not arguments.chunk_validation_command:
        raise RalphError(
            "New runtimes require --chunk-validation-command unless --disable-chunk-validation is explicit"
        )
    if (
        not arguments.disable_sprint_validation
        and not arguments.disable_tests
        and not (arguments.sprint_validation_command or arguments.test_command)
    ):
        raise RalphError(
            "New runtimes require --sprint-validation-command unless --disable-sprint-validation is explicit"
        )

    target.mkdir(parents=True, exist_ok=True)
    if config.is_symlink():
        raise RalphError(f"Refusing symlinked runtime configuration: {config}")
    checksums = copy_runtime(target, arguments.mode)
    config.write_text(render_config(arguments), encoding="utf-8")

    write_json(
        metadata_path,
        {
            "schema_version": "1.0",
            "runtime_version": runtime_version(),
            "mode": arguments.mode,
            "repositories": arguments.repos if arguments.mode == "multi-repo" else [],
            "managed_files": checksums,
            "previous_runtime_version": None,
        },
    )
    (target / "sprints").mkdir(exist_ok=True)
    (target / "logs").mkdir(exist_ok=True)
    return target


def parse_config(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise RalphError(f"config.env:{line_number} is not KEY=VALUE")
        key, value = line.split("=", 1)
        values[key] = value.strip().strip("'\"")
    return values


def update_config(text: str, updates: dict[str, str]) -> str:
    """Update shell assignments without disturbing operator comments or ordering."""
    remaining = dict(updates)
    output: list[str] = []
    for raw in text.splitlines():
        stripped = raw.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            key = stripped.split("=", 1)[0]
            if key in remaining:
                output.append(f"{key}={remaining.pop(key)}")
                continue
        output.append(raw)
    if remaining and output and output[-1]:
        output.append("")
    output.extend(f"{key}={value}" for key, value in remaining.items())
    return "\n".join(output) + "\n"


def remove_config_keys(text: str, keys: set[str]) -> str:
    output: list[str] = []
    for raw in text.splitlines():
        stripped = raw.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            key = stripped.split("=", 1)[0]
            if key in keys:
                continue
        output.append(raw)
    return "\n".join(output) + "\n"


def load_metadata(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def upgrade(arguments: argparse.Namespace) -> Path:
    """Refresh managed runtime files and migrate validation configuration safely."""
    repo = arguments.repo.resolve()
    target = repo / ".ralph"
    config_path = target / "config.env"
    metadata_path = target / ".runtime-manifest.json"
    if target.is_symlink() or not target.is_dir():
        raise RalphError(f"Runtime not found or unsafe: {target}")
    if config_path.is_symlink() or not config_path.is_file():
        raise RalphError(f"Runtime configuration not found or unsafe: {config_path}")

    metadata = load_metadata(metadata_path)
    config = parse_config(config_path)
    mode = metadata.get("mode") or config.get("RALPH_MODE", "monorepo")
    if mode not in MODES:
        raise RalphError(f"Unsupported installed runtime mode: {mode}")
    repositories = metadata.get("repositories", [])
    if not isinstance(repositories, list):
        repositories = []
    if mode == "multi-repo" and not repositories:
        repositories = config.get("RALPH_REPOS", "").split()

    chunk_command = (
        arguments.chunk_validation_command
        or config.get("RALPH_CHUNK_VALIDATION_COMMAND", "")
    )
    sprint_command = (
        arguments.sprint_validation_command
        or config.get("RALPH_SPRINT_VALIDATION_COMMAND", "")
        or config.get("RALPH_TEST_COMMAND", "")
    )
    model = arguments.model or config.get("RALPH_AGENT_MODEL", "")
    agent = arguments.agent or config.get("RALPH_AGENT", "")
    max_sprint_iterations = (
        arguments.max_sprint_iterations
        if arguments.max_sprint_iterations is not None
        else config.get("MAX_SPRINT_ITERATIONS")
        or config.get("MAX_ITERATIONS")
    )
    max_chunk_iterations = (
        arguments.max_chunk_iterations
        if arguments.max_chunk_iterations is not None
        else config.get("MAX_CHUNK_ITERATIONS")
    )
    agent, model, max_sprint_iterations, max_chunk_iterations = (
        resolve_upgrade_operator_choices(
            agent, model, max_sprint_iterations, max_chunk_iterations
        )
    )
    for label, value in (
        ("MAX_SPRINT_ITERATIONS", str(max_sprint_iterations)),
        ("MAX_CHUNK_ITERATIONS", str(max_chunk_iterations)),
    ):
        if not value.isdigit() or int(value) < 1:
            raise RalphError(f"{label} must be a positive integer")
    chunk_enabled = (
        "false"
        if arguments.disable_chunk_validation
        else (
            "true"
            if arguments.chunk_validation_command
            else config.get("RALPH_CHUNK_VALIDATION_ENABLED", "true")
        )
    )
    sprint_enabled = (
        "false"
        if arguments.disable_sprint_validation
        else (
            "true"
            if arguments.sprint_validation_command
            else config.get(
                "RALPH_SPRINT_VALIDATION_ENABLED",
                config.get("RALPH_TESTS_ENABLED", "true"),
            )
        )
    )
    if chunk_enabled == "true" and not chunk_command:
        raise RalphError(
            "Upgrade requires --chunk-validation-command unless --disable-chunk-validation is explicit"
        )
    if sprint_enabled == "true" and not sprint_command:
        raise RalphError(
            "Upgrade requires --sprint-validation-command unless --disable-sprint-validation is explicit"
        )

    # Validate every managed destination before changing any runtime file.
    sources = runtime_sources(mode)
    resolved_target = target.resolve()
    for relative in sources:
        destination = target / relative
        if destination.is_symlink():
            raise RalphError(f"Refusing to replace managed symlink: {destination}")
        if not destination.parent.resolve().is_relative_to(resolved_target):
            raise RalphError(f"Refusing managed path outside runtime: {destination}")

    migrated = update_config(
        remove_config_keys(
            config_path.read_text(encoding="utf-8"),
            {"RALPH_UNATTENDED_APPROVED", "MAX_ITERATIONS"},
        ),
        {
            "RALPH_MODE": mode,
            "RALPH_AGENT": agent,
            "RALPH_AGENT_MODEL": shell_value(model),
            "MAX_SPRINT_ITERATIONS": str(max_sprint_iterations),
            "MAX_CHUNK_ITERATIONS": str(max_chunk_iterations),
            "RALPH_CHUNK_VALIDATION_ENABLED": chunk_enabled,
            "RALPH_SPRINT_VALIDATION_ENABLED": sprint_enabled,
            "RALPH_CHUNK_VALIDATION_COMMAND": shell_value(chunk_command),
            "RALPH_SPRINT_VALIDATION_COMMAND": shell_value(sprint_command),
        },
    )
    checksums = copy_runtime(target, mode)
    temporary_config = config_path.with_name(".config.env.tmp")
    temporary_config.write_text(migrated, encoding="utf-8")
    temporary_config.replace(config_path)
    write_json(
        metadata_path,
        {
            "schema_version": "1.0",
            "runtime_version": runtime_version(),
            "mode": mode,
            "repositories": repositories,
            "managed_files": checksums,
            "previous_runtime_version": metadata.get("runtime_version"),
        },
    )
    return target


def validate_sprint(
    path: Path, mode: str = "monorepo", repositories: tuple[str, ...] = ()
) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    required = (
        "README.md",
        "IMPLEMENTATION_PLAN.md",
        "relevant-specs.md",
        "chunks.json",
        "prompt.md",
        "SCRATCHPAD.md",
    )
    for name in required:
        if not (path / name).is_file():
            findings.append(
                {
                    "status": "fail",
                    "check": f"sprint:{path.name}:{name}",
                    "detail": "missing",
                }
            )
    chunks_path = path / "chunks.json"
    if chunks_path.exists():
        try:
            payload = json.loads(chunks_path.read_text(encoding="utf-8"))
            chunks = payload.get("chunks")
            if not isinstance(chunks, list) or not chunks:
                raise RalphError("chunks must be a non-empty array")
            ids = [chunk.get("id") for chunk in chunks if isinstance(chunk, dict)]
            if ids != list(range(1, len(chunks) + 1)):
                raise RalphError("chunk IDs must be sequential integers starting at 1")
            for chunk in chunks:
                if not isinstance(chunk.get("passes"), bool):
                    raise RalphError(f"chunk {chunk.get('id')} passes must be boolean")
                if not isinstance(chunk.get("acceptance_criteria"), list):
                    raise RalphError(
                        f"chunk {chunk.get('id')} acceptance_criteria must be an array"
                    )
                artifacts = chunk.get("artifacts")
                if not isinstance(artifacts, (list, dict)):
                    raise RalphError(
                        f"chunk {chunk.get('id')} artifacts must be an array or repository map"
                    )
                if mode == "multi-repo":
                    owner = chunk.get("repo")
                    if owner not in {*repositories, "all", "both"}:
                        raise RalphError(
                            f"chunk {chunk.get('id')} repo must name a configured repository, all, or both"
                        )
            findings.append(
                {
                    "status": "pass",
                    "check": f"sprint:{path.name}:chunks",
                    "detail": f"{len(chunks)} sequential chunks",
                }
            )
        except (json.JSONDecodeError, RalphError) as error:
            findings.append(
                {
                    "status": "fail",
                    "check": f"sprint:{path.name}:chunks",
                    "detail": str(error),
                }
            )
    prompt_path = path / "prompt.md"
    if prompt_path.exists():
        prompt = prompt_path.read_text(encoding="utf-8")
        for token in ("SCRATCHPAD.md", "RALPH_CHUNK_COMPLETE"):
            if token not in prompt:
                findings.append(
                    {
                        "status": "fail",
                        "check": f"sprint:{path.name}:prompt",
                        "detail": f"missing {token}",
                    }
                )
    return findings


def validate(repo: Path) -> dict[str, Any]:
    root = repo.resolve() / ".ralph"
    findings: list[dict[str, str]] = []
    for command in ("bash", "git", "jq"):
        executable = shutil.which(command)
        findings.append(
            {
                "status": "pass" if executable else "fail",
                "check": f"prerequisite:{command}",
                "detail": executable or "not found on PATH",
            }
        )
    python_executable = None
    for command in ("python3", "python"):
        candidate = shutil.which(command)
        if candidate and subprocess.run(
            [candidate, "-c", "import sys; raise SystemExit(sys.version_info < (3, 11))"],
            check=False,
            capture_output=True,
        ).returncode == 0:
            python_executable = candidate
            break
    findings.append(
        {
            "status": "pass" if python_executable else "fail",
            "check": "prerequisite:python",
            "detail": python_executable or "Python 3.11+ not found as python3 or python",
        }
    )
    metadata_path = root / ".runtime-manifest.json"
    metadata: dict[str, Any] = {}
    if metadata_path.is_file():
        try:
            value = json.loads(metadata_path.read_text(encoding="utf-8"))
            if isinstance(value, dict):
                metadata = value
        except json.JSONDecodeError:
            metadata = {}
    mode = metadata.get("mode", "monorepo")
    try:
        sources = runtime_sources(mode)
    except RalphError:
        sources = runtime_sources("monorepo")
        findings.append({"status": "fail", "check": "runtime:mode", "detail": f"unsupported mode: {mode}"})
    for relative in sources:
        path = root / relative
        findings.append(
            {
                "status": "pass" if path.is_file() else "fail",
                "check": f"runtime:{relative}",
                "detail": "present" if path.is_file() else "missing",
            }
        )
    if metadata_path.is_file():
        try:
            expected = metadata.get("managed_files", {})
            drift = [
                relative
                for relative, checksum in expected.items()
                if not (root / relative).is_file()
                or sha256(root / relative) != checksum
            ]
            findings.append(
                {
                    "status": "fail" if drift else "pass",
                    "check": "runtime:fingerprint",
                    "detail": "drift: " + ", ".join(drift)
                    if drift
                    else "managed runtime matches installation manifest",
                }
            )
        except (json.JSONDecodeError, OSError) as error:
            findings.append(
                {"status": "fail", "check": "runtime:fingerprint", "detail": str(error)}
            )
    else:
        findings.append(
            {
                "status": "warn",
                "check": "runtime:fingerprint",
                "detail": "installation manifest missing",
            }
        )
    installed_version = metadata.get("runtime_version")
    expected_version = runtime_version()
    findings.append(
        {
            "status": "pass" if installed_version == expected_version else "fail",
            "check": "runtime:version",
            "detail": expected_version
            if installed_version == expected_version
            else f"installed {installed_version or 'unknown'}; available {expected_version}; run upgrade",
        }
    )
    config_path = root / "config.env"
    if not config_path.is_file():
        findings.append(
            {"status": "fail", "check": "config", "detail": "missing .ralph/config.env"}
        )
        config: dict[str, str] = {}
    else:
        try:
            config = parse_config(config_path)
            findings.append(
                {
                    "status": "pass",
                    "check": "config",
                    "detail": "parseable KEY=VALUE configuration",
                }
            )
        except RalphError as error:
            config = {}
            findings.append({"status": "fail", "check": "config", "detail": str(error)})
    config_mode = config.get("RALPH_MODE", mode)
    if config_mode != mode:
        findings.append(
            {
                "status": "fail",
                "check": "runtime:mode",
                "detail": f"manifest mode={mode} config mode={config_mode}",
            }
        )
    else:
        findings.append({"status": "pass", "check": "runtime:mode", "detail": mode})
    repositories = tuple(config.get("RALPH_REPOS", "").split())
    if mode == "multi-repo":
        if len(repositories) < 2:
            findings.append(
                {
                    "status": "fail",
                    "check": "repositories",
                    "detail": "RALPH_REPOS requires at least two entries",
                }
            )
        for name in repositories:
            child = repo.resolve() / name
            findings.append(
                {
                    "status": "pass" if (child / ".git").exists() else "fail",
                    "check": f"repository:{name}",
                    "detail": str(child),
                }
            )
    agent = config.get("RALPH_AGENT", "")
    if agent not in AGENTS:
        findings.append(
            {
                "status": "fail",
                "check": "agent",
                "detail": f"unsupported RALPH_AGENT={agent or 'missing'}",
            }
        )
    elif agent == "custom" and not config.get("RALPH_AGENT_COMMAND"):
        findings.append(
            {
                "status": "fail",
                "check": "agent",
                "detail": "custom agent requires RALPH_AGENT_COMMAND",
            }
        )
    else:
        executable = config.get("RALPH_AGENT_COMMAND") or shutil.which(agent)
        findings.append(
            {
                "status": "pass" if executable else "fail",
                "check": "agent",
                "detail": agent
                if executable
                else f"{agent} executable not found on PATH",
            }
        )
    if agent in AGENTS - {"custom"} and not config.get("RALPH_AGENT_MODEL"):
        findings.append(
            {
                "status": "fail",
                "check": "agent-model",
                "detail": "standard harness requires explicit RALPH_AGENT_MODEL",
            }
        )
    elif agent:
        findings.append(
            {
                "status": "pass",
                "check": "agent-model",
                "detail": config.get("RALPH_AGENT_MODEL") or "owned by custom command",
            }
        )
    for key in ("MAX_SPRINT_ITERATIONS", "MAX_CHUNK_ITERATIONS"):
        raw_budget = config.get(key, "")
        valid_budget = raw_budget.isdigit() and int(raw_budget) > 0
        findings.append(
            {
                "status": "pass" if valid_budget else "fail",
                "check": f"budget:{key.lower()}",
                "detail": raw_budget if valid_budget else "must be a positive integer",
            }
        )
    if config.get("RALPH_CHUNK_VALIDATION_ENABLED", "true") == "true" and not config.get(
        "RALPH_CHUNK_VALIDATION_COMMAND"
    ):
        findings.append(
            {
                "status": "fail",
                "check": "chunk-validation",
                "detail": "enabled but RALPH_CHUNK_VALIDATION_COMMAND is empty",
            }
        )
    sprint_command = config.get("RALPH_SPRINT_VALIDATION_COMMAND") or config.get(
        "RALPH_TEST_COMMAND"
    )
    sprint_enabled = config.get(
        "RALPH_SPRINT_VALIDATION_ENABLED",
        config.get("RALPH_TESTS_ENABLED", "true"),
    )
    if sprint_enabled == "true" and not sprint_command:
        findings.append(
            {
                "status": "fail",
                "check": "sprint-validation",
                "detail": "enabled but RALPH_SPRINT_VALIDATION_COMMAND is empty",
            }
        )
    sprints = root / "sprints"
    if sprints.is_dir():
        sprint_paths = sorted(path for path in sprints.iterdir() if path.is_dir())
        current_sprint = config.get("CURRENT_SPRINT", "")
        if sprint_paths and not current_sprint:
            findings.append(
                {
                    "status": "fail",
                    "check": "current-sprint",
                    "detail": "CURRENT_SPRINT is empty",
                }
            )
        elif current_sprint and not (sprints / current_sprint).is_dir():
            findings.append(
                {
                    "status": "fail",
                    "check": "current-sprint",
                    "detail": f"sprint directory not found: {current_sprint}",
                }
            )
        elif current_sprint:
            findings.append(
                {"status": "pass", "check": "current-sprint", "detail": current_sprint}
            )
        for sprint in sprint_paths:
            findings.extend(validate_sprint(sprint, mode, repositories))
    failed = sum(item["status"] == "fail" for item in findings)
    warned = sum(item["status"] == "warn" for item in findings)
    return {
        "ok": failed == 0,
        "failed": failed,
        "warnings": warned,
        "findings": findings,
    }


def print_validation(report: dict[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(report, indent=2))
        return
    for item in report["findings"]:
        print(f"{item['status'].upper():4}  {item['check']}: {item['detail']}")
    print(f"Summary: {report['failed']} failed, {report['warnings']} warnings")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    init_parser = subparsers.add_parser(
        "init", help="Install the runtime without overwriting sprint state."
    )
    init_parser.add_argument("--repo", type=Path, default=Path.cwd())
    init_parser.add_argument("--mode", choices=sorted(MODES), default="monorepo")
    init_parser.add_argument(
        "--repos",
        nargs="+",
        default=[],
        metavar="NAME",
        help="Child repository directory names for multi-repo mode.",
    )
    init_parser.add_argument("--primary-repo")
    init_parser.add_argument("--agent", choices=sorted(AGENTS))
    init_parser.add_argument("--model")
    init_parser.add_argument(
        "--agent-command",
        help="Trusted custom shell command; receives RALPH_PROMPT_FILE and RALPH_PROJECT_ROOT.",
    )
    init_parser.add_argument("--chunk-validation-command")
    init_parser.add_argument("--sprint-validation-command")
    init_parser.add_argument(
        "--test-command",
        help="Deprecated alias for --sprint-validation-command.",
    )
    init_parser.add_argument("--e2e-command")
    init_parser.add_argument("--max-sprint-iterations", type=int)
    init_parser.add_argument("--max-chunk-iterations", type=int)
    init_parser.add_argument("--disable-review", action="store_true")
    init_parser.add_argument("--disable-documentation", action="store_true")
    init_parser.add_argument("--disable-tests", action="store_true")
    init_parser.add_argument("--disable-chunk-validation", action="store_true")
    init_parser.add_argument("--disable-sprint-validation", action="store_true")
    init_parser.add_argument("--update-runtime", action="store_true", help=argparse.SUPPRESS)
    upgrade_parser = subparsers.add_parser(
        "upgrade", help="Safely refresh an installed runtime and migrate validation gates."
    )
    upgrade_parser.add_argument("--repo", type=Path, default=Path.cwd())
    upgrade_parser.add_argument("--agent", choices=sorted(AGENTS))
    upgrade_parser.add_argument("--model")
    upgrade_parser.add_argument("--max-sprint-iterations", type=int)
    upgrade_parser.add_argument("--max-chunk-iterations", type=int)
    upgrade_parser.add_argument("--chunk-validation-command")
    upgrade_parser.add_argument("--sprint-validation-command")
    upgrade_parser.add_argument("--disable-chunk-validation", action="store_true")
    upgrade_parser.add_argument("--disable-sprint-validation", action="store_true")
    validate_parser = subparsers.add_parser(
        "validate", help="Validate runtime, configuration, and sprints."
    )
    validate_parser.add_argument("--repo", type=Path, default=Path.cwd())
    validate_parser.add_argument("--json", action="store_true")
    status_parser = subparsers.add_parser(
        "status", help="Run the installed runtime status command."
    )
    status_parser.add_argument("--repo", type=Path, default=Path.cwd())
    status_parser.add_argument("--sprint")
    return parser


def main() -> int:
    arguments = build_parser().parse_args()
    try:
        if arguments.command == "init":
            existed = (arguments.repo.resolve() / ".ralph").is_dir()
            target = install(arguments)
            config = parse_config(target / "config.env")
            action = "Upgraded" if existed else "Installed"
            print(f"{action} Ralph runtime {runtime_version()}: {target}")
            print(
                f"Harness={config.get('RALPH_AGENT') or 'unset'} "
                f"model={config.get('RALPH_AGENT_MODEL') or 'custom-command'} "
                f"sprint-turns={config.get('MAX_SPRINT_ITERATIONS') or 'unset'} "
                f"chunk-turns={config.get('MAX_CHUNK_ITERATIONS') or 'unset'}"
            )
            return 0
        if arguments.command == "validate":
            report = validate(arguments.repo)
            print_validation(report, arguments.json)
            return 0 if report["ok"] else 1
        if arguments.command == "upgrade":
            target = upgrade(arguments)
            print(f"Upgraded Ralph runtime to {runtime_version()}: {target}")
            print("Operator configuration and sprint state were preserved.")
            return 0
        status = arguments.repo.resolve() / ".ralph" / "status.sh"
        if not status.is_file():
            raise RalphError(f"Runtime not found: {status}")
        command = [str(status)]
        if arguments.sprint:
            command.append(arguments.sprint)
        return subprocess.run(
            command, cwd=arguments.repo.resolve(), check=False
        ).returncode
    except (OSError, RalphError) as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
