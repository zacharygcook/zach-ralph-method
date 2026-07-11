# Initialize or Audit a Ralph Loop

Use when setting up `.ralph/` for a new project or auditing an existing setup.

First determine topology. Monorepo mode installs into one Git repository. Multi-repo mode installs
into a shared parent containing two or more independent child Git repositories and requires
`--mode multi-repo --repos <names...> --primary-repo <name>`.

## Required checks

1. Ensure the equivalent core structure exists:

   - `.ralph/loop.sh`
   - `.ralph/status.sh`
   - `.ralph/lib/ralph-common.sh`
   - `.ralph/hooks/post-sprint.sh`
   - `.ralph/hooks/review.sh`
   - `.ralph/hooks/document.sh`
   - `.ralph/hooks/test.sh` (compatibility filename for final validation)
   - `.ralph/prompts/*.md`

2. Ensure hardened loop behavior is present:

   - completion reconciliation on exit/signals
   - orchestration log file per run
   - heartbeat and structured event logs
   - stale hook state and lock recovery
   - post-result stall recovery without a wall-clock cap on legitimate long runs
   - completion detection from scoped markers plus exact sequential `chunks.json` transitions
   - required chunk validation and chunk-owned commit evidence before acceptance

3. Ensure manifest schema supports resumability:

   - `phase`: `running|chunks_done|hooks_done`
   - `validation.chunk_attempts` evidence
   - `hooks.review|documentation|validation` statuses

4. Ensure post-sprint idempotency:

   - marker files in sprint dirs: `.hook-review.done`, `.hook-documentation.done`, `.hook-validation.done`
   - disabled hooks are explicitly `skipped`, never mislabeled as executed

5. Ensure `SCRATCHPAD.md` is treated as persistent sprint memory:

   - prompts tell agents to read it first and append before finishing.

6. Ensure safety and portability:

   - the harness, exact model, and reasoning choice are explicit for standard adapters
   - sprint and per-chunk agent-turn budgets are positive and operator-reviewed
   - broad auto-commit is disabled
   - project-specific chunk/sprint/E2E commands live in `config.env`, not the runtime
   - `bash`, `git`, `jq`, and Python 3 are present
   - multi-repo chunks name a configured repository or `all`, and each repository keeps an independent commit boundary

Vendor a new package with `npx skills add zacharygcook/zach-ralph-method`, or refresh a locked package with `npx skills update ralph-workflows --project`. Then use the vendored `scripts/ralph` launcher to initialize or upgrade the stateful project runtime and run `validate` before live execution. In multi-repo mode, ensure project-supplied validation commands cover contracts that cross repository boundaries.
