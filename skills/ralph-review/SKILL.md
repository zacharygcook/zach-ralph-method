---
name: ralph-review
description: Critically review a current or completed Ralph sprint for specification alignment, implementation correctness, validation evidence, orchestration reliability, and remaining gaps. Use when the user asks to review, audit, accept, or assess a Ralph sprint. Do not implement fixes unless the user separately authorizes them.
---

# Ralph Review

Review the sprint as an evidence-backed delivery unit.

1. Read repository instructions, the durable spec, sprint `README.md`, `IMPLEMENTATION_PLAN.md`,
   `relevant-specs.md`, `chunks.json`, and `SCRATCHPAD.md`.
2. Inspect the actual commit range and changed artifacts. Do not accept summaries as proof.
3. Verify every passed chunk against its acceptance criteria, validation logs, and commit evidence.
4. Check final review, documentation, sprint-validation, and optional E2E hook states. Distinguish
   skipped, failed, interrupted, and completed hooks.
5. Look for missing spec behavior, accidental scope, weak tests, stale documentation, unsafe
   orchestration state, and negative knowledge the next sprint must preserve.
6. Report findings by severity, then give a clear verdict: complete, repairable before acceptance, or
   blocked. Name the exact evidence and next action.

Do not rewrite chunk state, manufacture evidence, or implement findings during a review-only request.
When installed beside `$ralph-loop`, consult `references/review.md` for the full shared rubric.
