---
name: ralph-sprint
description: Create, repair, validate, or advance a Ralph sprint from a repository specification. Use when the user asks for the first or next sprint, sprint planning, spec breakdown, chunk design, CURRENT_SPRINT selection, or preparation after a completed sprint. Never start the autonomous loop unless separately requested.
---

# Ralph Sprint

Prepare exactly one reviewable sprint and stop before execution.

1. Read repository agent instructions, the durable `SPEC.md` or equivalent, `.ralph/config.env`, and
   all existing sprint state.
2. If the current sprint is incomplete or its hooks failed, repair or resume it instead of creating a
   competing sprint.
3. Select the next dependency-ordered slice of the spec. Do not create speculative future sprint
   folders.
4. Create or validate `README.md`, `IMPLEMENTATION_PLAN.md`, `relevant-specs.md`, `chunks.json`,
   `prompt.md`, and `SCRATCHPAD.md` under `.ralph/sprints/<number-name>/`.
5. Keep chunks sequential and bounded. Give each concrete acceptance criteria, accurate artifact
   paths, and repository ownership in multi-repo mode.
6. Set `CURRENT_SPRINT`, run `just validate` when available, and repair every setup defect.
7. Summarize the goal, chunks, validation, risks, and operator review path. Do not run `just run`.

When installed beside `$ralph-loop`, its `references/spec-breakdown.md`, `references/sprint.md`, and
`references/chunks.md` provide the complete shared contract. Preserve those invariants even when the
umbrella skill is unavailable.
