---
name: ralph-workflows
description: Initialize, plan, run, inspect, and review resumable Ralph-style autonomous implementation loops with sequential chunks, persistent scratchpad memory, manifests, and idempotent post-sprint hooks. Use for `.ralph` orchestration or similar long-running coding-agent sprint systems.
---

# Ralph Workflows

Operate an autonomous implementation loop as a resumable state machine, not a one-shot prompt. Preserve negative knowledge, make progress machine-readable, and distinguish completed implementation chunks from completed review/documentation/test hooks.

## Deterministic runtime

Vendor this skill into a project with the upstream Skills CLI:

```bash
npx skills@latest add zacharygcook/zach-ralph-method --skill ralph-workflows --copy -y
```

The CLI detects the active coding agent and creates a project-local skill copy containing the
instructions, installer, and runtime templates. Use `--agent <name>` only to target a specific agent;
`--agent '*'` deliberately creates adapter copies for every supported client. Run the bundled
installer from the detected skill directory.

Install the bundled hardened Bash runtime only when the user asks to initialize or repair Ralph:

```bash
python3 <skill-dir>/scripts/ralph.py init --repo <repository> --agent <agent> --chunk-validation-command '<fast repo-native command>' --sprint-validation-command '<full repo-native command>'
```

For a parent directory containing independent child Git repositories, use multi-repo mode:

```bash
python3 <skill-dir>/scripts/ralph.py init --repo <parent> --mode multi-repo --repos <repo-a> <repo-b> --primary-repo <repo-a> --agent <agent> --chunk-validation-command '<fast cross-repo command>' --sprint-validation-command '<full cross-repo command>'
```

Initialization is non-destructive: it refuses an existing `.ralph/` unless `--update-runtime` is
explicit, preserves configuration and sprint state during an update, and leaves autonomous execution
disarmed. Add `--approve-unattended` only when the user has authorized an autonomous run. Disable a
hook explicitly when it is genuinely outside the repository's workflow; skipped hooks remain visible
in the manifest instead of being reported as completed work.

Upgrade an existing runtime without replacing operator configuration, sprints, logs, or scratchpad
state. Legacy `RALPH_TEST_COMMAND` values migrate to the sprint validation gate; a missing chunk gate
must be supplied or explicitly disabled:

```bash
python3 <skill-dir>/scripts/ralph.py upgrade --repo <repository> --chunk-validation-command '<fast repo-native command>' --sprint-validation-command '<full repo-native command>'
```

Validate installed runtime, fingerprints, configuration, and sprint structure with:

```bash
python3 <skill-dir>/scripts/ralph.py validate --repo <repository>
python3 <skill-dir>/scripts/ralph.py status --repo <repository>
```

Use `--agent custom --agent-command '<command>'` for another client. The trusted command receives
`RALPH_PROMPT_FILE` and `RALPH_PROJECT_ROOT`. Never place secrets in `config.env`; Bash sources it as
code. Runtime adapters support Codex, Claude Code, Amp, OpenCode, and Factory Droid, but verify the
installed CLI's current flags before a live autonomous run.

A repository may call the same fast command from its existing pre-commit system for earlier feedback.
That hook complements Ralph; it never replaces the independent gate because hooks can be absent,
bypassed, or inappropriate for slow and multi-repository validation. Ralph does not install Husky or
another language-specific hook manager.

## Route the Task

- New setup or reliability audit: [references/initialize.md](references/initialize.md)
- Turn a spec into dependent sprints: [references/spec-breakdown.md](references/spec-breakdown.md)
- Create or validate a sprint folder: [references/sprint.md](references/sprint.md)
- Design `chunks.json`: [references/chunks.md](references/chunks.md)
- Determine real completion: [references/status.md](references/status.md)
- Critically review a sprint: [references/review.md](references/review.md)

Read only the references needed for the requested operation.

## Shared Invariants

- Chunks are sequential, bounded, and have concrete acceptance criteria plus validation commands.
- Completion markers are candidates: accept exactly one next sequential chunk only after the configured fast validation and chunk-owned commit evidence pass.
- Failed chunk validation resets only that claim, records structured evidence, and gives the next fresh context a repair handoff through `SCRATCHPAD.md`.
- Artifact paths are accurate because downstream hooks depend on them.
- Every sprint has persistent scratchpad memory; agents read it first and append decisions, dead ends, and discoveries before exiting.
- Manifests represent resumable phases and hook status explicitly.
- Review, documentation, and final validation hooks are idempotent and leave durable completion markers.
- Hook runtime state belongs under the run log, outside sprint work products.
- Signals and interrupted exits reconcile state instead of silently losing completed work.
- A sprint is not complete merely because implementation chunks pass; required post-sprint hooks must also finish.
- Final sprint validation runs after review and documentation mutations; optional E2E runs last.
- Automatic broad Git staging is off. Do not enable `RALPH_AUTO_COMMIT=I_ACCEPT_GIT_ADD_ALL` in a
  repository with concurrent dirty work; prefer agent-created scoped commits.
- Multi-repo chunks name a configured child repository or `all`; manifests retain independent start
  and end commit ranges, and agents commit separately inside each changed repository.

Adapt filenames when a repository uses an equivalent orchestration convention, but preserve these semantics.
