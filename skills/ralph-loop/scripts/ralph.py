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

SCRIPT_DIRECTORY = Path(__file__).resolve().parent
if str(SCRIPT_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIRECTORY))

from advance_sprint import AdvanceError, NoNextSprint, next_sprint


ROOT = Path(__file__).resolve().parent.parent
PACKAGE_LAYOUT = (ROOT / "assets" / "templates").is_dir()
TEMPLATES = ROOT / "assets" / "templates" if PACKAGE_LAYOUT else ROOT / "templates"
VERSION_FILE = ROOT / "assets" / "VERSION" if PACKAGE_LAYOUT else ROOT / "VERSION"
SHARED_FILES = {
    "VERSION": VERSION_FILE,
    "advance.py": ROOT / "scripts" / "advance_sprint.py",
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
AGENTS = {"amp", "claude", "codex", "droid", "grok", "opencode", "custom"}
REASONING_AGENTS = {"claude", "codex", "droid", "grok", "opencode"}
STATE_MODES = {"tracked", "local"}
MODEL_SUGGESTIONS: dict[str, tuple[tuple[str, str], ...]] = {
    "codex": (
        ("gpt-5.5", "excellent cost/capability balance"),
        ("gpt-5.6-terra", "strong general-purpose coding"),
        ("gpt-5.6-sol", "deeper difficult work"),
        ("gpt-5.4", "proven general-purpose option"),
        ("gpt-5.3-codex", "coding-specialized option"),
    ),
    "claude": (
        ("claude-opus-4-8", "highest-capability Opus option"),
        ("claude-opus-4-8-fast", "faster Opus option"),
        ("claude-fable-5", "Fable option"),
        ("claude-sonnet-5", "current Sonnet option"),
        ("claude-sonnet-4-6", "established Sonnet option"),
    ),
    "droid": (
        ("claude-opus-4-8", "highest-capability Claude option"),
        ("gpt-5.5", "excellent cost/capability balance"),
        ("gpt-5.4", "proven general-purpose option"),
        ("gpt-5.3-codex", "coding-specialized option"),
        ("grok-4.5", "strong alternative model family"),
    ),
    "grok": (
        ("grok-4.5", "current default powering Grok Build"),
        ("grok-composer-2.5-fast", "fast Composer option"),
        ("grok-4.3", "general reasoning model"),
        ("grok-build-0.1", "coding-focused API model"),
    ),
    "amp": (
        ("smart", "Amp chooses the model and tools"),
        ("deep", "more deliberate difficult work"),
        ("rush", "fast iteration"),
        ("large", "large-context work"),
        ("free", "free-tier mode"),
    ),
}
REASONING_SUGGESTIONS: dict[str, tuple[tuple[str, str], ...]] = {
    "codex": (
        ("medium", "balanced everyday work"),
        ("high", "difficult debugging or architecture"),
        ("low", "faster straightforward chunks"),
        ("xhigh", "unusually hard problems"),
        ("inherit", "explicitly use your Codex configuration"),
    ),
    "claude": (
        ("high", "difficult implementation work"),
        ("medium", "balanced everyday work"),
        ("low", "faster straightforward chunks"),
        ("xhigh", "very difficult problems"),
        ("max", "maximum supported effort"),
        ("inherit", "explicitly use your Claude configuration"),
    ),
    "droid": (
        ("medium", "balanced everyday work when supported"),
        ("high", "difficult implementation work"),
        ("low", "faster straightforward chunks when supported"),
        ("xhigh", "very difficult problems when supported"),
        ("inherit", "explicitly use the selected model's default"),
    ),
    "grok": (
        ("medium", "balanced coding work"),
        ("high", "difficult debugging or architecture"),
        ("low", "faster straightforward chunks"),
        ("none", "no additional reasoning when supported"),
        ("inherit", "explicitly use the selected model's default"),
    ),
    "opencode": (
        ("medium", "balanced provider variant when available"),
        ("high", "deeper provider variant when available"),
        ("low", "faster provider variant when available"),
        ("inherit", "explicitly use the configured provider variant"),
    ),
}


class RalphError(ValueError):
    pass


def prompt_choice(label: str, choices: set[str]) -> str:
    ordered = ", ".join(sorted(choices))
    while True:
        value = input(f"{label} ({ordered}): ").strip()
        if value in choices:
            return value
        print(f"Choose one of: {ordered}", file=sys.stderr)


def prompt_recommended_value(
    label: str, suggestions: tuple[tuple[str, str], ...]
) -> str:
    print(f"\n{label} suggestions:")
    for index, (value, description) in enumerate(suggestions, 1):
        print(f"  {index}. {value} — {description}")
    print("  Or type another exact value.")
    while True:
        value = input(f"{label}: ").strip()
        if value.isdigit() and 1 <= int(value) <= len(suggestions):
            return suggestions[int(value) - 1][0]
        if value:
            return value
        print("Choose a number or type an exact value.", file=sys.stderr)


def discover_harness_models(agent: str) -> tuple[str, ...]:
    """Best-effort local discovery; onboarding never depends on it succeeding."""
    if not shutil.which(agent):
        return ()
    try:
        if agent == "droid":
            command = ["droid", "exec", "--help"]
        elif agent == "opencode":
            command = ["opencode", "models"]
        elif agent == "grok":
            command = ["grok", "models"]
        else:
            return ()
        result = subprocess.run(
            command, check=False, capture_output=True, text=True, timeout=5
        )
    except (OSError, subprocess.TimeoutExpired):
        return ()
    output = result.stdout + "\n" + result.stderr
    if agent == "opencode":
        return tuple(
            line.split()[0]
            for line in output.splitlines()
            if line.strip() and "/" in line.split()[0]
        )
    if agent == "grok":
        available = output.partition("Available models:")[2]
        return tuple(
            line.lstrip(" *-").split()[0]
            for line in available.splitlines()
            if line.lstrip().startswith(("* ", "- "))
        )
    available = output.partition("Available Models:")[2].partition("Model details:")[0]
    return tuple(
        line.split()[0]
        for line in available.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    )


def model_suggestions(agent: str) -> tuple[tuple[str, str], ...]:
    curated = MODEL_SUGGESTIONS.get(agent, ())
    discovered = discover_harness_models(agent)
    if not discovered:
        return curated
    discovered_set = set(discovered)
    suggestions = [item for item in curated if item[0] in discovered_set]
    known = {value for value, _ in suggestions}
    suggestions.extend(
        (value, "available from the installed harness")
        for value in discovered
        if value not in known
    )
    return tuple(suggestions[:5])


def prompt_model(agent: str) -> str:
    noun = "Amp mode" if agent == "amp" else "Model"
    suggestions = model_suggestions(agent)
    if suggestions:
        return prompt_recommended_value(noun, suggestions)
    return input(f"Exact {noun.lower()}: ").strip()


def prompt_reasoning(agent: str) -> str:
    return prompt_recommended_value(
        "Reasoning effort", REASONING_SUGGESTIONS[agent]
    )


def prompt_positive_integer(
    label: str, guidance: tuple[tuple[int, str], ...] = ()
) -> int:
    if guidance:
        print(f"\n{label} guidance:")
        for value, description in guidance:
            print(f"  {value} — {description}")
    while True:
        value = input(f"{label}: ").strip()
        if value.isdigit() and int(value) > 0:
            return int(value)
        print("Enter a positive integer.", file=sys.stderr)


def prompt_command(label: str) -> str:
    value = input(f"{label}: ").strip()
    if not value:
        raise RalphError(f"{label} cannot be empty")
    return value


def prompt_state_mode() -> str:
    print("\nRalph state storage:")
    print("  1. tracked — commit durable sprint state and share it through Git")
    print("  2. local — keep the entire .ralph runtime out of Git")
    while True:
        value = input("State storage: ").strip().lower()
        if value in {"1", "tracked"}:
            return "tracked"
        if value in {"2", "local"}:
            return "local"
        print("Choose 1/tracked or 2/local.", file=sys.stderr)


def resolve_validation_commands(
    chunk_enabled: bool,
    chunk_command: str,
    sprint_enabled: bool,
    sprint_command: str,
    context: str,
) -> tuple[str, str]:
    missing = []
    if chunk_enabled and not chunk_command:
        missing.append("--chunk-validation-command")
    if sprint_enabled and not sprint_command:
        missing.append("--sprint-validation-command")
    if not missing:
        return chunk_command, sprint_command
    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        raise RalphError(
            f"Missing validation choices for noninteractive {context}: "
            + ", ".join(missing)
        )
    print("Configure repository validation. No commands are assumed.")
    if chunk_enabled and not chunk_command:
        chunk_command = prompt_command("Fast command to validate each chunk")
    if sprint_enabled and not sprint_command:
        sprint_command = prompt_command(
            "Comprehensive command to validate the completed sprint"
        )
    return chunk_command, sprint_command


def resolve_init_operator_choices(arguments: argparse.Namespace) -> None:
    """Collect missing operator intent interactively or fail clearly in automation."""
    missing = []
    if not arguments.agent:
        missing.append("--agent")
    if arguments.agent != "custom" and not arguments.model:
        missing.append("--model")
    if (not arguments.agent or arguments.agent in REASONING_AGENTS) and not arguments.reasoning_effort:
        missing.append("--reasoning-effort")
    if arguments.max_sprint_iterations is None:
        missing.append("--max-sprint-iterations")
    if arguments.max_chunk_iterations is None:
        missing.append("--max-chunk-iterations")
    if not arguments.state_mode:
        missing.append("--state-mode")
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
        arguments.model = prompt_model(arguments.agent)
        if not arguments.model:
            raise RalphError("An explicit model is required for a standard harness")
    if arguments.agent in REASONING_AGENTS and not arguments.reasoning_effort:
        arguments.reasoning_effort = prompt_reasoning(arguments.agent)
    if arguments.max_chunk_iterations is None:
        arguments.max_chunk_iterations = prompt_positive_integer(
            "Maximum agent turns per chunk",
            (
                (3, "small, sharply scoped chunks"),
                (5, "balanced starting point"),
                (8, "difficult refactors or uncertain work"),
            ),
        )
    if arguments.max_sprint_iterations is None:
        arguments.max_sprint_iterations = prompt_positive_integer(
            "Maximum agent turns across the sprint",
            (
                (15, "small sprint"),
                (30, "typical sprint"),
                (60, "large or exploratory sprint"),
            ),
        )
    if not arguments.state_mode:
        arguments.state_mode = prompt_state_mode()


def resolve_upgrade_operator_choices(
    agent: str,
    model: str,
    reasoning_effort: str,
    max_sprint_iterations: int | str | None,
    max_chunk_iterations: int | str | None,
) -> tuple[str, str, str, int | str, int | str]:
    """Repair incomplete stored operator intent without inventing values."""
    missing = []
    if agent not in AGENTS:
        missing.append("--agent")
    if agent != "custom" and not model:
        missing.append("--model")
    if (agent not in AGENTS or agent in REASONING_AGENTS) and not reasoning_effort:
        missing.append("--reasoning-effort")
    if max_sprint_iterations is None or str(max_sprint_iterations) == "":
        missing.append("--max-sprint-iterations")
    if max_chunk_iterations is None or str(max_chunk_iterations) == "":
        missing.append("--max-chunk-iterations")
    if not missing:
        return agent, model, reasoning_effort, max_sprint_iterations, max_chunk_iterations
    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        raise RalphError("Missing operator choices for upgrade: " + ", ".join(missing))
    print("Configure missing Ralph operator controls. No choices are assumed.")
    if agent not in AGENTS:
        agent = prompt_choice("Agent harness", AGENTS)
    if agent != "custom" and not model:
        model = prompt_model(agent)
        if not model:
            raise RalphError("An explicit model is required for a standard harness")
    if agent in REASONING_AGENTS and not reasoning_effort:
        reasoning_effort = prompt_reasoning(agent)
    if max_chunk_iterations is None or str(max_chunk_iterations) == "":
        max_chunk_iterations = prompt_positive_integer(
            "Maximum agent turns per chunk",
            ((3, "small chunks"), (5, "balanced"), (8, "difficult chunks")),
        )
    if max_sprint_iterations is None or str(max_sprint_iterations) == "":
        max_sprint_iterations = prompt_positive_integer(
            "Maximum agent turns across the sprint",
            ((15, "small sprint"), (30, "typical sprint"), (60, "large sprint")),
        )
    return agent, model, reasoning_effort, max_sprint_iterations, max_chunk_iterations


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def runtime_version() -> str:
    return VERSION_FILE.read_text(encoding="utf-8").strip()


def git_info_exclude(repo: Path) -> Path | None:
    result = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "--git-path", "info/exclude"],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    path = Path(result.stdout.strip())
    return path if path.is_absolute() else repo / path


def configure_state_visibility(repo: Path, state_mode: str) -> None:
    if state_mode not in STATE_MODES:
        raise RalphError(f"Unsupported state mode: {state_mode}")
    exclude = git_info_exclude(repo)
    if exclude is None:
        if state_mode == "tracked":
            raise RalphError("Tracked Ralph state requires the orchestration root to be a Git repository")
        return
    tracked_state = subprocess.run(
        ["git", "-C", str(repo), "ls-files", ".ralph"],
        check=False,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if state_mode == "local" and tracked_state:
        raise RalphError(
            "Cannot switch to local state while .ralph files are tracked; "
            "remove them from the Git index intentionally, then rerun upgrade"
        )
    begin = "# BEGIN ralph-loop local state"
    end = "# END ralph-loop local state"
    text = exclude.read_text(encoding="utf-8") if exclude.exists() else ""
    output: list[str] = []
    inside = False
    for line in text.splitlines():
        if line == begin:
            inside = True
            continue
        if line == end:
            inside = False
            continue
        if not inside:
            output.append(line)
    while output and not output[-1]:
        output.pop()
    if output:
        output.append("")
    pattern = "/.ralph/" if state_mode == "local" else "/.ralph/logs/"
    output.extend((begin, pattern, end))
    exclude.parent.mkdir(parents=True, exist_ok=True)
    exclude.write_text("\n".join(output) + "\n", encoding="utf-8")


def infer_state_mode(repo: Path) -> str:
    tracked = subprocess.run(
        ["git", "-C", str(repo), "ls-files", "--error-unmatch", ".ralph/config.env"],
        check=False,
        capture_output=True,
    )
    if tracked.returncode == 0:
        return "tracked"
    ignored = subprocess.run(
        ["git", "-C", str(repo), "check-ignore", "--no-index", "-q", ".ralph/config.env"],
        check=False,
    )
    return "local" if ignored.returncode == 0 else ""


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
            "RALPH_AGENT_REASONING": shell_value(
                arguments.reasoning_effort
                if arguments.agent in REASONING_AGENTS
                else ("owned-by-amp-mode" if arguments.agent == "amp" else "custom-command")
            ),
            "RALPH_AGENT_COMMAND": shell_value(arguments.agent_command or ""),
            "RALPH_STATE_MODE": arguments.state_mode,
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
        "# Generated by the ralph-loop skill. This file is sourced by Bash; treat it as trusted code."
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
    if arguments.agent in REASONING_AGENTS and not arguments.reasoning_effort:
        raise RalphError(
            "New runtimes require --reasoning-effort for the selected agent harness"
        )
    if arguments.max_sprint_iterations < 1 or arguments.max_chunk_iterations < 1:
        raise RalphError("Iteration budgets must be positive integers")
    chunk_enabled = not arguments.disable_chunk_validation
    sprint_enabled = not arguments.disable_sprint_validation and not arguments.disable_tests
    arguments.chunk_validation_command, arguments.sprint_validation_command = (
        resolve_validation_commands(
            chunk_enabled,
            arguments.chunk_validation_command or "",
            sprint_enabled,
            arguments.sprint_validation_command or arguments.test_command or "",
            "init",
        )
    )

    configure_state_visibility(repo, arguments.state_mode)
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
            "state_mode": arguments.state_mode,
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
    reasoning_effort = (
        arguments.reasoning_effort
        or config.get("RALPH_AGENT_REASONING", "")
    )
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
    state_mode = (
        arguments.state_mode
        or config.get("RALPH_STATE_MODE", "")
        or metadata.get("state_mode", "")
        or infer_state_mode(repo)
    )
    if state_mode not in STATE_MODES:
        if sys.stdin.isatty() and sys.stdout.isatty():
            state_mode = prompt_state_mode()
        else:
            raise RalphError("Missing operator choice for upgrade: --state-mode")
    agent, model, reasoning_effort, max_sprint_iterations, max_chunk_iterations = (
        resolve_upgrade_operator_choices(
            agent,
            model,
            reasoning_effort,
            max_sprint_iterations,
            max_chunk_iterations,
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
        or getattr(arguments, "disable_tests", False)
        else (
            "true"
            if arguments.sprint_validation_command
            else config.get(
                "RALPH_SPRINT_VALIDATION_ENABLED",
                config.get("RALPH_TESTS_ENABLED", "true"),
            )
        )
    )
    chunk_command, sprint_command = resolve_validation_commands(
        chunk_enabled == "true",
        chunk_command,
        sprint_enabled == "true",
        sprint_command,
        "upgrade",
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
            {
                "RALPH_UNATTENDED_APPROVED",
                "RALPH_INTERACTIVE",
                "RALPH_INTERACTIVE_TIMEOUT_SEC",
                "MAX_ITERATIONS",
            },
        ),
        {
            "RALPH_MODE": mode,
            "RALPH_AGENT": agent,
            "RALPH_AGENT_MODEL": shell_value(model),
            "RALPH_AGENT_REASONING": shell_value(
                reasoning_effort
                if agent in REASONING_AGENTS
                else ("owned-by-amp-mode" if agent == "amp" else "custom-command")
            ),
            "MAX_SPRINT_ITERATIONS": str(max_sprint_iterations),
            "MAX_CHUNK_ITERATIONS": str(max_chunk_iterations),
            "RALPH_STATE_MODE": state_mode,
            "RALPH_CHUNK_VALIDATION_ENABLED": chunk_enabled,
            "RALPH_SPRINT_VALIDATION_ENABLED": sprint_enabled,
            "RALPH_CHUNK_VALIDATION_COMMAND": shell_value(chunk_command),
            "RALPH_SPRINT_VALIDATION_COMMAND": shell_value(sprint_command),
        },
    )
    configure_state_visibility(repo, state_mode)
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
            "state_mode": state_mode,
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
    if agent in REASONING_AGENTS and not config.get("RALPH_AGENT_REASONING"):
        findings.append(
            {
                "status": "fail",
                "check": "agent-reasoning",
                "detail": "selected harness requires explicit RALPH_AGENT_REASONING",
            }
        )
    elif agent:
        findings.append(
            {
                "status": "pass",
                "check": "agent-reasoning",
                "detail": config.get("RALPH_AGENT_REASONING")
                or ("owned by Amp mode" if agent == "amp" else "owned by custom command"),
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
    state_mode = config.get("RALPH_STATE_MODE", "")
    if state_mode not in STATE_MODES:
        findings.append(
            {
                "status": "fail",
                "check": "state-mode",
                "detail": "RALPH_STATE_MODE must be tracked or local",
            }
        )
    else:
        git_root = git_info_exclude(repo.resolve()) is not None
        tracked_state = subprocess.run(
            ["git", "-C", str(repo.resolve()), "ls-files", ".ralph"],
            check=False,
            capture_output=True,
            text=True,
        ).stdout.strip()
        ignored = subprocess.run(
            ["git", "-C", str(repo.resolve()), "check-ignore", "--no-index", "-q", ".ralph/config.env"],
            check=False,
        ).returncode == 0
        matches = (
            state_mode == "local"
            and not tracked_state
            and (ignored or not git_root)
        ) or (
            state_mode == "tracked" and not ignored
        )
        findings.append(
            {
                "status": "pass" if matches else "fail",
                "check": "state-mode",
                "detail": (
                    f"{state_mode}; no parent Git repository"
                    if not git_root
                    else f"{state_mode}; .ralph is {'ignored' if ignored else 'visible to Git'}"
                ),
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
    init_parser.add_argument("--reasoning-effort")
    init_parser.add_argument("--state-mode", choices=sorted(STATE_MODES))
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
    upgrade_parser.add_argument("--reasoning-effort")
    upgrade_parser.add_argument("--state-mode", choices=sorted(STATE_MODES))
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
    advance_parser = subparsers.add_parser(
        "advance", help="Safely select the next prepared sprint."
    )
    advance_parser.add_argument("--repo", type=Path, default=Path.cwd())
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
                f"reasoning={config.get('RALPH_AGENT_REASONING') or 'unset'} "
                f"state={config.get('RALPH_STATE_MODE') or 'unset'} "
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
        if arguments.command == "advance":
            selected = next_sprint(arguments.repo.resolve() / ".ralph", apply=True)
            print(f"Selected next sprint: {selected}")
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
    except NoNextSprint as error:
        print(str(error), file=sys.stderr)
        return 3
    except (OSError, RalphError, AdvanceError) as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
