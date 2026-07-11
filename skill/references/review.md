# Review Sprint Readiness and Completion

Use when asked to review sprint quality/readiness before or after execution.

## Inputs

- Sprint path
- Spec path (or equivalent source of truth)

## Review posture

- Be skeptical by default.
- Assume incompleteness until validated.
- Prioritize concrete, high-impact findings with file references.

## Required checks

1. Internal consistency and spec alignment

   - Endpoints/routes/types/schema/env/permissions naming consistency.
   - Drift across sprint docs, chunks, prompt, and implementation.

2. Execution risk and correctness

   - Validation boundaries, error handling, retries, idempotency.
   - Data flow/state transitions and race-condition risks.
   - Integration assumptions (auth/session, third-party limits, webhooks, fallback paths).

3. Test realism

   - Coverage is aligned to acceptance criteria.
   - External dependencies are mocked/isolated appropriately.

4. SCRATCHPAD enforcement

   - `SCRATCHPAD.md` exists in sprint directory.
   - `prompt.md` instructs agents to read scratchpad first and append learnings before finishing.
   - If missing, flag as reliability gap.

5. Hardened post-sprint orchestration state

   - `manifest.json` contains `phase` and `hooks` statuses.
   - Hook marker files are present or absence is explained:
     - `.hook-review.done`
     - `.hook-documentation.done`
     - `.hook-tests.done`
   - Latest `orchestrator.log` shows completion/reconciliation flow.
   - If chunks are complete but hooks are not, flag as automation gap.

## Deliverable format

1. Findings ordered by severity with file references.
2. Concrete fixes (specific edits/process changes).
3. Readiness score 1-5 with rationale.

## Scoring guidance

- Start from conservative readiness.
- Score above 3 only with strong evidence of cross-file consistency, test credibility, and orchestration completeness.
