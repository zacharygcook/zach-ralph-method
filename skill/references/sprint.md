# Create or Validate a Sprint

Use when creating a new sprint under `.ralph/sprints/`.

## Required sprint files

- `README.md`
- `IMPLEMENTATION_PLAN.md`
- `relevant-specs.md`
- `chunks.json`
- `prompt.md`
- `SCRATCHPAD.md`

## Non-negotiables

1. `SCRATCHPAD.md` is mandatory memory across context resets.
2. `prompt.md` must instruct: read scratchpad first, append learnings before exit.
3. `chunks.json` must include accurate `artifacts`; review/doc/test hooks depend on them.
4. Sprint should be resumable: avoid assumptions that require uninterrupted execution.
5. Configure a fast chunk gate and a comprehensive final sprint gate; do not rely only on agent-reported validation.
