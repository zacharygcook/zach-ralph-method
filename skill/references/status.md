# Determine Real Sprint Status

Use when users ask whether a sprint is truly complete.

## Read

- `.ralph/config.env`
- `.ralph/sprints/<current>/chunks.json`
- `.ralph/sprints/<current>/manifest.json`
- hook markers in sprint dir
- latest `.ralph/logs/<current>/run-*/orchestrator.log`

## Completion logic

- `all chunks pass` is not sufficient by itself.
- Sprint is fully complete only when `manifest.phase == hooks_done`, every accepted chunk has successful validation evidence, and every enabled post-sprint hook
  is done. Explicitly disabled hooks remain visible as `skipped`.
- If chunks pass but hooks are incomplete, recommend safe rerun: `./.ralph/loop.sh`.
- Prefer `python3 <skill-dir>/scripts/ralph.py status --repo <repository>` for a portable summary.
