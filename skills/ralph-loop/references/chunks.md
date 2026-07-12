# Design Sequential Chunks

Use when producing or revising `chunks.json`.

## Rules

1. Chunks are strictly sequential.
2. Each chunk has concrete acceptance criteria and explicit validation commands where possible.
3. Each chunk includes accurate `artifacts` paths.
4. Criteria should support downstream post-sprint review/docs/tests.
5. Remind agents to record dead ends and decisions in `SCRATCHPAD.md`.
6. One iteration may mark only the next sequential chunk passed. Ralph independently validates and requires commit evidence before acceptance.
