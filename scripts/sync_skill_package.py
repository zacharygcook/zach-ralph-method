#!/usr/bin/env python3
"""Build or verify the self-contained Skills CLI package in ``skill/``."""

from __future__ import annotations

import argparse
import filecmp
import shutil
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
MAPPINGS = {
    ROOT / "scripts" / "ralph.py": ROOT / "skill" / "scripts" / "ralph.py",
    ROOT / "VERSION": ROOT / "skill" / "assets" / "VERSION",
    ROOT / "templates": ROOT / "skill" / "assets" / "templates",
}


def paths_match(source: Path, destination: Path) -> bool:
    if source.is_file():
        return destination.is_file() and source.read_bytes() == destination.read_bytes()
    if not destination.is_dir():
        return False
    comparison = filecmp.dircmp(source, destination)
    return not (
        comparison.left_only
        or comparison.right_only
        or comparison.diff_files
        or comparison.funny_files
        or any(
            not paths_match(source / name, destination / name)
            for name in comparison.common_dirs
        )
    )


def sync() -> None:
    for source, destination in MAPPINGS.items():
        if destination.exists():
            if destination.is_dir():
                shutil.rmtree(destination)
            else:
                destination.unlink()
        destination.parent.mkdir(parents=True, exist_ok=True)
        if source.is_dir():
            shutil.copytree(
                source,
                destination,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"),
            )
        else:
            shutil.copy2(source, destination)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("sync", "check"))
    arguments = parser.parse_args()
    if arguments.mode == "sync":
        sync()
    stale = [
        str(destination.relative_to(ROOT))
        for source, destination in MAPPINGS.items()
        if not paths_match(source, destination)
    ]
    if stale:
        print("Stale skill package: " + ", ".join(stale), file=sys.stderr)
        return 1
    print("Self-contained skill package matches canonical runtime.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
