#!/usr/bin/env python3
"""Format Codex exec --json JSONL output for real-time visibility."""

import json
import sys
import os
import atexit

# ANSI colors
CYAN = "\033[36m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
MAGENTA = "\033[35m"
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

# Track state
current_items = {}  # id -> item data
thread_id = None


def truncate(s, max_len=100):
    """Truncate string with ellipsis."""
    s = str(s).replace("\n", " ")
    return s[: max_len - 3] + "..." if len(s) > max_len else s


def format_item_start(item):
    """Format an item.started event."""
    item_type = item.get("type", "unknown")
    if item_type == "command_execution":
        cmd = item.get("command", "")
        print(f"\n{CYAN}$ {cmd}{RESET}", flush=True)
        log_summary(f"CMD: {truncate(cmd, 80)}")

    elif item_type == "reasoning":
        print(f"\n{MAGENTA}thinking...{RESET}", end="", flush=True)

    elif item_type == "file_change":
        path = item.get("path", item.get("file", ""))
        action = item.get("action", "modify")
        print(f"\n{YELLOW}{action}: {path}{RESET}", end="", flush=True)
        log_summary(f"FILE: {action} {path}")

    elif item_type == "mcp_tool_call":
        tool = item.get("tool", item.get("name", "mcp_tool"))
        print(f"\n{CYAN}mcp:{tool}{RESET}", end="", flush=True)
        log_summary(f"MCP: {tool}")

    elif item_type == "web_search":
        query = item.get("query", "")
        print(f"\n{CYAN}search: {query}{RESET}", end="", flush=True)
        log_summary(f"SEARCH: {truncate(query, 60)}")


def format_item_update(item):
    """Format an item.updated event (streaming updates)."""
    item_type = item.get("type", "unknown")

    if item_type == "reasoning":
        # Show reasoning summary as it streams
        summary = item.get("summary", "")
        if summary:
            # Clear the "thinking..." and show summary
            print(f"\r{MAGENTA}{truncate(summary, 80)}{RESET}", end="", flush=True)

    elif item_type == "agent_message":
        # Stream text as it comes
        text = item.get("text", "")
        if text:
            print(text, end="", flush=True)


def format_item_complete(item):
    """Format an item.completed event."""
    item_type = item.get("type", "unknown")
    if item_type == "command_execution":
        exit_code = item.get("exit_code", item.get("status", ""))
        output = item.get("output", item.get("stdout", ""))
        if exit_code == 0 or exit_code == "success":
            print(f" {GREEN}ok{RESET}")
            if output:
                # Show truncated output
                for line in str(output).split("\n")[:3]:
                    print(f"  {DIM}{truncate(line, 80)}{RESET}")
        else:
            print(f" {RED}exit {exit_code}{RESET}")
            stderr = item.get("stderr", output)
            if stderr:
                print(f"  {RED}{truncate(stderr, 100)}{RESET}")
            log_summary(f"  -> ERROR: exit {exit_code}")

    elif item_type == "reasoning":
        summary = item.get("summary", "")
        if summary:
            print(f"\r{MAGENTA}{truncate(summary, 80)}{RESET}")
            log_summary(f"THINK: {truncate(summary, 60)}")
        else:
            print()  # Clear the "thinking..." line

    elif item_type == "agent_message":
        text = item.get("text", "")
        if text:
            print(f"\n{text}")
            log_summary(f"MSG: {truncate(text, 80)}")

    elif item_type == "file_change":
        status = item.get("status", "done")
        print(f" {GREEN}{status}{RESET}")

    elif item_type == "mcp_tool_call":
        result = item.get("result", "")
        print(f" {GREEN}ok{RESET}")
        if result:
            print(f"  {DIM}{truncate(result, 80)}{RESET}")

    elif item_type == "web_search":
        results = item.get("results", [])
        count = len(results) if isinstance(results, list) else 0
        print(f" {GREEN}{count} results{RESET}")

    elif item_type == "error":
        msg = item.get("message", item.get("error", str(item)))
        print(f"\n{RED}ERROR: {msg}{RESET}")
        log_summary(f"ERROR: {truncate(msg, 80)}")


def format_turn_complete(data):
    """Format turn.completed with usage stats."""
    usage = data.get("usage", {})
    if usage:
        input_t = usage.get("input_tokens", 0)
        output_t = usage.get("output_tokens", 0)
        reasoning_t = usage.get("reasoning_output_tokens", 0)
        cached_t = usage.get("cached_input_tokens", 0)

        parts = [f"in:{input_t}"]
        if cached_t:
            parts.append(f"cached:{cached_t}")
        if reasoning_t:
            parts.append(f"reasoning:{reasoning_t}")
        parts.append(f"out:{output_t}")

        print(f"\n{DIM}tokens: {' '.join(parts)}{RESET}")
        log_summary(f"TOKENS: {' '.join(parts)}")


# Main loop
for line in sys.stdin:
    line = line.strip()
    if not line:
        continue

    try:
        data = json.loads(line)
    except json.JSONDecodeError:
        # Not JSON, print as-is (might be stderr mixed in)
        print(line)
        continue

    event_type = data.get("type", "")

    if event_type == "thread.started":
        thread_id = data.get("thread_id", "unknown")
        print(f"{DIM}Thread: {thread_id}{RESET}")
        print()

    elif event_type == "turn.started":
        pass  # Quiet

    elif event_type == "turn.completed":
        format_turn_complete(data)

    elif event_type == "turn.failed":
        error = data.get("error", data.get("message", "unknown error"))
        print(f"\n{RED}Turn failed: {error}{RESET}")
        log_summary(f"FAILED: {truncate(error, 80)}")

    elif event_type == "item.started":
        item = data.get("item", {})
        item_id = item.get("id", "")
        current_items[item_id] = item
        format_item_start(item)

    elif event_type == "item.updated":
        item = data.get("item", {})
        item_id = item.get("id", "")
        # Merge with existing item data
        if item_id in current_items:
            current_items[item_id].update(item)
        else:
            current_items[item_id] = item
        format_item_update(item)

    elif event_type == "item.completed":
        item = data.get("item", {})
        item_id = item.get("id", "")
        # Merge with existing item data
        if item_id in current_items:
            current_items[item_id].update(item)
            item = current_items[item_id]
        format_item_complete(item)
        # Clean up
        current_items.pop(item_id, None)

    elif event_type == "error":
        error = data.get("error", data.get("message", str(data)))
        print(f"\n{RED}Error: {error}{RESET}")
        log_summary(f"ERROR: {truncate(error, 80)}")

# Final summary
if summary_lines:
    log_summary("")
    log_summary("=" * 60)
