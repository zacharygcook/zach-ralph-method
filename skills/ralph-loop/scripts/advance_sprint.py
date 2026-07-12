#!/usr/bin/env python3
"""Safely select the next prepared Ralph sprint."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any


REQUIRED_SPRINT_FILES = (
    "README.md",
    "IMPLEMENTATION_PLAN.md",
    "relevant-specs.md",
    "chunks.json",
    "prompt.md",
    "SCRATCHPAD.md",
)
SPRINT_NAME = re.compile(r"^(?P<number>[0-9]+)-[A-Za-z0-9][A-Za-z0-9._-]*$")


class AdvanceError(ValueError):
    """The runtime cannot safely advance."""


class NoNextSprint(AdvanceError):
    """No sequential prepared sprint exists."""


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise AdvanceError(f"Cannot read {path}: {error}") from error
    if not isinstance(value, dict):
        raise AdvanceError(f"Expected a JSON object: {path}")
    return value


def read_current_sprint(config_path: Path) -> str:
    matches: list[str] = []
    try:
        lines = config_path.read_text(encoding="utf-8").splitlines()
    except OSError as error:
        raise AdvanceError(f"Cannot read {config_path}: {error}") from error
    for raw in lines:
        line = raw.strip()
        if line.startswith("CURRENT_SPRINT="):
            matches.append(line.split("=", 1)[1].strip().strip("'\""))
    if len(matches) != 1 or not matches[0]:
        raise AdvanceError("config.env must contain exactly one non-empty CURRENT_SPRINT")
    if not SPRINT_NAME.fullmatch(matches[0]):
        raise AdvanceError(f"Invalid CURRENT_SPRINT name: {matches[0]}")
    return matches[0]


def read_config_value(config_path: Path, key: str) -> str:
    for raw in config_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line.startswith(f"{key}="):
            return line.split("=", 1)[1].strip().strip("'\"")
    return ""


def sprint_chunks(sprint: Path) -> list[dict[str, Any]]:
    value = read_json(sprint / "chunks.json").get("chunks")
    if not isinstance(value, list) or not value:
        raise AdvanceError(f"Sprint has no chunks: {sprint.name}")
    chunks: list[dict[str, Any]] = []
    for index, chunk in enumerate(value, 1):
        if not isinstance(chunk, dict) or chunk.get("id") != index:
            raise AdvanceError(f"Sprint chunks must have sequential IDs: {sprint.name}")
        chunks.append(chunk)
    return chunks


def require_completed(sprint: Path) -> None:
    manifest = read_json(sprint / "manifest.json")
    if manifest.get("phase") != "hooks_done":
        raise AdvanceError(f"Current sprint hooks are not complete: {sprint.name}")
    if not all(chunk.get("passes") is True for chunk in sprint_chunks(sprint)):
        raise AdvanceError(f"Current sprint still has incomplete chunks: {sprint.name}")


def require_prepared(sprint: Path) -> None:
    missing = [name for name in REQUIRED_SPRINT_FILES if not (sprint / name).is_file()]
    if missing:
        raise AdvanceError(
            f"Next sprint is not prepared ({sprint.name}); missing: {', '.join(missing)}"
        )
    sprint_chunks(sprint)


def find_next(runtime: Path, current: str) -> Path:
    match = SPRINT_NAME.fullmatch(current)
    if match is None:
        raise AdvanceError(f"Invalid current sprint name: {current}")
    next_number = int(match.group("number")) + 1
    candidates = sorted(
        path
        for path in (runtime / "sprints").glob(f"{next_number}-*")
        if path.is_dir() and SPRINT_NAME.fullmatch(path.name)
    )
    if not candidates:
        raise NoNextSprint(f"No prepared sprint {next_number} found")
    if len(candidates) > 1:
        names = ", ".join(path.name for path in candidates)
        raise AdvanceError(f"Multiple sprint {next_number} candidates found: {names}")
    require_prepared(candidates[0])
    return candidates[0]


def replace_current_sprint(config_path: Path, next_sprint: str) -> str:
    original = config_path.read_text(encoding="utf-8")
    lines = original.splitlines()
    replacements = 0
    output: list[str] = []
    for raw in lines:
        if raw.strip().startswith("CURRENT_SPRINT="):
            output.append(f"CURRENT_SPRINT={next_sprint}")
            replacements += 1
        else:
            output.append(raw)
    if replacements != 1:
        raise AdvanceError("Refusing ambiguous CURRENT_SPRINT update")

    descriptor, temporary_name = tempfile.mkstemp(
        prefix=".config.env.", suffix=".tmp", dir=config_path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write("\n".join(output) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        temporary.chmod(config_path.stat().st_mode)
        temporary.replace(config_path)
    finally:
        temporary.unlink(missing_ok=True)
    return original


def commit_config(runtime: Path, next_sprint: str, original: str) -> None:
    config_path = runtime / "config.env"
    if read_config_value(config_path, "RALPH_STATE_MODE") != "tracked":
        return
    repo = runtime.parent
    relative = config_path.relative_to(repo)
    add = subprocess.run(
        ["git", "-C", str(repo), "add", "--", str(relative)],
        check=False,
        capture_output=True,
        text=True,
    )
    if add.returncode == 0:
        commit = subprocess.run(
            [
                "git",
                "-C",
                str(repo),
                "commit",
                "--only",
                "-m",
                f"Advance Ralph to sprint {next_sprint}",
                "--",
                str(relative),
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        if commit.returncode == 0:
            return
        detail = commit.stderr.strip() or commit.stdout.strip()
    else:
        detail = add.stderr.strip() or add.stdout.strip()
    config_path.write_text(original, encoding="utf-8")
    subprocess.run(
        ["git", "-C", str(repo), "restore", "--staged", "--", str(relative)],
        check=False,
        capture_output=True,
    )
    raise AdvanceError(f"Could not commit tracked sprint selection: {detail}")


def next_sprint(runtime: Path, *, apply: bool) -> str:
    runtime = runtime.resolve()
    config_path = runtime / "config.env"
    current = read_current_sprint(config_path)
    current_path = runtime / "sprints" / current
    if not current_path.is_dir():
        raise AdvanceError(f"Current sprint directory not found: {current}")
    candidate = find_next(runtime, current)
    if apply:
        require_completed(current_path)
        original = replace_current_sprint(config_path, candidate.name)
        commit_config(runtime, candidate.name, original)
    return candidate.name


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--runtime",
        type=Path,
        default=Path(__file__).resolve().parent,
        help="Installed .ralph runtime directory.",
    )
    parser.add_argument(
        "--show-next",
        action="store_true",
        help="Print the next prepared sprint without changing config.env.",
    )
    arguments = parser.parse_args()
    try:
        print(next_sprint(arguments.runtime, apply=not arguments.show_next))
        return 0
    except NoNextSprint as error:
        print(str(error))
        return 3
    except (AdvanceError, OSError) as error:
        print(str(error))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
