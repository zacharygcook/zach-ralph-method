# Prepare the First Ralph Sprint

Use when an operator has installed the skill but has not yet prepared or run a sprint.

## Preflight

- Read repository agent instructions and the durable `SPEC.md` or equivalent.
- Confirm the repository has a known Git baseline without unexplained concurrent work.
- Confirm Bash, Git, `jq`, Python 3, and the configured coding-agent CLI are available.
- Identify a fast repository-native command for every chunk and a comprehensive final command for the
  completed sprint. Do not invent placeholder validation that always passes.
- If the spec or credible validation is missing, explain the gap and stop before autonomous setup.

## Prepare

1. Initialize or safely upgrade `.ralph/` with the bundled runtime.
2. Keep `RALPH_UNATTENDED_APPROVED=false`.
3. Decompose the spec into dependency-ordered sprints without creating speculative later sprint
   folders.
4. Create the first sprint with `README.md`, `IMPLEMENTATION_PLAN.md`, `relevant-specs.md`,
   `chunks.json`, `prompt.md`, and `SCRATCHPAD.md`.
5. Set `CURRENT_SPRINT` in `.ralph/config.env`.
6. Run the bundled validator and repair setup defects.
7. Summarize the sprint goal, chunks, validation, risks, and exact operator review path. Do not start
   the loop without explicit authorization.

The operator supplies intent and authorization. The skill owns deterministic runtime installation,
sprint-folder construction, active-sprint configuration, and pre-run validation.
