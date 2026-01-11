#!/usr/bin/env python3
"""Format Claude stream-json output to look like the TUI."""
import json
import sys

# ANSI colors
CYAN = "\033[36m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
DIM = "\033[2m"
BOLD = "\033[1m"
RESET = "\033[0m"

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
                    for k, v in params.items():
                        if isinstance(v, str) and len(v) > 60:
                            v = v[:57] + "..."
                        print(f" {DIM}{k}={v}{RESET}", end="")
                except:
                    pass
                print()
            current_tool = None
            current_input = ""

    elif msg_type == "user":
        # Tool result
        result = data.get("tool_use_result", "")
        if result:
            if "Error" in str(result):
                print(f"  {YELLOW}⚠ {result}{RESET}")
            else:
                # Truncate long results
                if len(str(result)) > 100:
                    result = str(result)[:97] + "..."
                print(f"  {GREEN}✓ {result}{RESET}")

    elif msg_type == "result":
        print()
        print(f"{DIM}{'─' * 60}{RESET}")
        print(f"{BOLD}Result:{RESET} {data.get('result', '')[:200]}")
        cost = data.get("total_cost_usd", 0)
        duration = data.get("duration_ms", 0) / 1000
        print(f"{DIM}Cost: ${cost:.4f} | Duration: {duration:.1f}s{RESET}")
