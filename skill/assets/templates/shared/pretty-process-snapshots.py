#!/usr/bin/env python3
"""Pretty-print Ralph process_snapshot events from events.jsonl."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROW_RE = re.compile(r"^\s*(\d+)\s+(\d+)\s+(\d+)\s+(\S+)\s+(\S+)\s+(.*)$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render process_snapshot entries from Ralph events.jsonl",
    )
    parser.add_argument(
        "events_file",
        type=Path,
        help="Path to events.jsonl",
    )
    parser.add_argument(
        "--failed-only",
        action="store_true",
        help="Show only failed snapshots",
    )
    return parser.parse_args()


def print_snapshot(timestamp: str, status: str, message: str) -> None:
    label, _, raw_rows = message.partition(" :: ")
    print(f"[{timestamp}] status={status} label={label}")
    print("  PID    PPID   PGID   STAT  ELAPSED  COMMAND")
    for row in raw_rows.split("; "):
        row = row.strip()
        if not row:
            continue
        match = ROW_RE.match(row)
        if not match:
            print(f"  {row}")
            continue
        pid, ppid, pgid, stat, elapsed, command = match.groups()
        print(f"  {pid:<6} {ppid:<6} {pgid:<6} {stat:<5} {elapsed:<8} {command}")
    print()


def main() -> int:
    args = parse_args()
    if not args.events_file.exists():
        print(f"File not found: {args.events_file}", file=sys.stderr)
        return 1

    count = 0
    with args.events_file.open("r", encoding="utf-8") as handle:
        for raw in handle:
            raw = raw.strip()
            if not raw:
                continue
            try:
                event = json.loads(raw)
            except json.JSONDecodeError:
                continue

            if event.get("type") != "process_snapshot":
                continue
            status = str(event.get("status", "unknown"))
            if args.failed_only and status != "failed":
                continue

            ts = str(event.get("timestamp", "unknown"))
            message = str(event.get("message", ""))
            print_snapshot(ts, status, message)
            count += 1

    if count == 0:
        filter_note = " (failed-only filter applied)" if args.failed_only else ""
        print(f"No process_snapshot events found{filter_note}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
