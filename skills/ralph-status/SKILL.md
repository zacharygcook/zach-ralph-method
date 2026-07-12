---
name: ralph-status
description: Report truthful Ralph loop progress from runtime state, chunks, manifests, hooks, markers, commits, and logs. Use when the user asks what Ralph is doing, whether a sprint or chunk finished, why it stopped, whether it is safe to resume, or what remains. This is read-only unless the user separately requests repair.
---

# Ralph Status

Report evidence, not optimism.

1. Run `just status` when the project exposes it; otherwise inspect `.ralph/status.sh` and
   `.ralph/config.env` directly.
2. Read the active sprint's `chunks.json`, `manifest.json`, `SCRATCHPAD.md`, hook markers, latest run
   logs, and relevant Git status/commits.
3. Distinguish chunk completion, all-chunks completion, hook completion, interruption, validation
   failure, exhausted turn budget, and full sprint completion.
4. Treat completion markers as claims. Confirm the expected sequential chunk transition, validation
   evidence, and commit boundary before calling work complete.
5. Report the current phase, completed and remaining chunks, hook state, latest meaningful event,
   blockers, and the exact safe next action.

Do not edit sprint state, rerun hooks, resume the loop, or mark chunks complete during a status request.
When installed beside `$ralph-loop`, consult `references/status.md` for the full shared state model.
