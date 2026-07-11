#!/usr/bin/env python3
"""Format Claude stream-json output to look like the TUI."""

import json
import sys
import os
import atexit

# ANSI colors
CYAN = "\033[36m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
DIM = "\033[2m"
BOLD = "\033[1m"
RESET = "\033[0m"

# Summary log (human-readable, separate from verbose JSON log)
SUMMARY_LOG = os.environ.get("SUMMARY_LOG")
summary_lines = []


def log_summary(line):
    """Add a line to the summary log."""
    if SUMMARY_LOG:
        summary_lines.append(line)


def write_summary():
    """Write summary log to file on exit."""
    if SUMMARY_LOG and summary_lines:
        try:
            with open(SUMMARY_LOG, "w") as f:
                f.write("\n".join(summary_lines) + "\n")
        except Exception as e:
            print(f"Warning: Could not write summary log: {e}", file=sys.stderr)


atexit.register(write_summary)

current_tool = None
current_input = ""

for line in sys.stdin:
    line = line.strip()
    if not line:
        continue
    try:
        data = json.loads(line)
    except json.JSONDecodeError:
        print(line)
        continue

    msg_type = data.get("type")

    if msg_type == "system" and data.get("subtype") == "init":
        print(f"{DIM}Session: {data.get('session_id', 'unknown')}{RESET}")
        print(f"{DIM}Model: {data.get('model', 'unknown')}{RESET}")
        print()

    elif msg_type == "stream_event":
        event = data.get("event", {})
        event_type = event.get("type")

        if event_type == "content_block_start":
            block = event.get("content_block", {})
            if block.get("type") == "tool_use":
                current_tool = block.get("name")
                current_input = ""
                print(f"\n{CYAN}▶ {current_tool}{RESET}", end="", flush=True)

        elif event_type == "content_block_delta":
            delta = event.get("delta", {})
            delta_type = delta.get("type")

            if delta_type == "text_delta":
                text = delta.get("text", "")
                print(text, end="", flush=True)

            elif delta_type == "input_json_delta":
                current_input += delta.get("partial_json", "")

        elif event_type == "content_block_stop":
            if current_tool and current_input:
                try:
                    params = json.loads(current_input)
                    # Show abbreviated params
                    param_strs = []
                    for k, v in params.items():
                        if isinstance(v, str) and len(v) > 60:
                            v = v[:57] + "..."
                        print(f" {DIM}{k}={v}{RESET}", end="")
                        param_strs.append(f"{k}={v}")
                    # Log to summary
                    log_summary(f"TOOL: {current_tool} {' '.join(param_strs)[:100]}")
                except (TypeError, ValueError):
                    log_summary(f"TOOL: {current_tool}")
                print()
            current_tool = None
            current_input = ""

    elif msg_type == "user":
        # Tool result
        result = data.get("tool_use_result", "")
        if result:
            result_str = str(result)
            if "Error" in result_str:
                print(f"  {YELLOW}⚠ {result}{RESET}")
                log_summary(f"  -> ERROR: {result_str[:80]}")
            else:
                # Truncate long results
                display = (
                    result_str[:97] + "..." if len(result_str) > 100 else result_str
                )
                print(f"  {GREEN}✓ {display}{RESET}")
                log_summary(f"  -> OK: {result_str[:80]}")

    elif msg_type == "result":
        print()
        print(f"{DIM}{'─' * 60}{RESET}")
        result_text = data.get("result", "")[:200]
        print(f"{BOLD}Result:{RESET} {result_text}")
        cost = data.get("total_cost_usd", 0)
        duration = data.get("duration_ms", 0) / 1000
        print(f"{DIM}Cost: ${cost:.4f} | Duration: {duration:.1f}s{RESET}")

        # Log final summary
        log_summary("")
        log_summary("=" * 60)
        log_summary(f"RESULT: {result_text}")
        log_summary(f"Cost: ${cost:.4f} | Duration: {duration:.1f}s")
