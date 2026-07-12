# Prepare the First Ralph Sprint

Use when an operator has installed the skill but has not yet prepared or run a sprint.

## Preflight

- Read repository agent instructions and the durable `SPEC.md` or equivalent.
- Confirm the repository has a known Git baseline without unexplained concurrent work.
- Confirm Bash, Git, `jq`, Python 3, and the configured coding-agent CLI are available.
- Confirm `just` is available and the root `justfile` imports the bundled Ralph recipes without
  replacing existing project recipes.
- Confirm the exact harness/model, reasoning choice, and positive sprint/per-chunk agent-turn budgets
  with the operator. Explain that 3/5/8 turns per chunk suit small/balanced/difficult work and that
  15/30/60 total turns suit small/typical/large sprints; these are guidance, not hidden defaults.
- Ask whether durable Ralph state should be `tracked` in Git or remain `local`; explain the
  reproducibility versus repository-noise tradeoff instead of assuming.
- Identify a fast repository-native command for every chunk and a comprehensive final command for the
  completed sprint. Do not invent placeholder validation that always passes.
- If the spec or credible validation is missing, explain the gap and stop before autonomous setup.

## Prepare

1. Initialize or safely upgrade `.ralph/` with the bundled runtime.
2. Decompose the spec into dependency-ordered sprints without creating speculative later sprint
   folders.
3. Create the first sprint with `README.md`, `IMPLEMENTATION_PLAN.md`, `relevant-specs.md`,
   `chunks.json`, `prompt.md`, and `SCRATCHPAD.md`.
4. Set `CURRENT_SPRINT` in `.ralph/config.env`.
5. In tracked mode, create a scoped setup commit containing the vendored skills, `justfile`, runtime,
   and prepared sprint before execution.
6. Run the bundled validator and repair setup defects.
7. Summarize the sprint goal, chunks, validation, risks, and exact operator review path. Stop before
   running `.ralph/loop.sh`; the operator starts the loop deliberately after review.

The operator supplies intent and starts the loop deliberately. The skill owns deterministic runtime installation,
sprint-folder construction, active-sprint configuration, and pre-run validation.
