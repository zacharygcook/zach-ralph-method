---
name: ralph-workflows
description: Initialize, plan, run, inspect, and review resumable Ralph-style autonomous implementation loops with sequential chunks, persistent scratchpad memory, manifests, and idempotent post-sprint hooks. Use for `.ralph` orchestration or similar long-running coding-agent sprint systems.
---

# Ralph Workflows

Operate an autonomous implementation loop as a resumable state machine, not a one-shot prompt. Preserve negative knowledge, make progress machine-readable, and distinguish completed implementation chunks from completed review/documentation/test hooks.

## First-use operator journey

When a user asks how to start, preflight the repository instead of explaining sprint internals first:

1. Confirm a Git repository; Bash, Git, `jq`, and Python 3; an explicit harness, model, and reasoning
   choice (or a fully owned custom command); positive sprint and per-chunk turn budgets; a durable `SPEC.md` or
   equivalent; and credible fast chunk plus comprehensive sprint validation commands. Node.js/npm
   and `npx` are required when the skill still needs to be installed or updated.
2. Read repository agent instructions and the spec before choosing commands or planning work.
3. Ensure `just` is available and install the project recipe import without overwriting an existing
   `justfile`; then initialize or upgrade the deterministic runtime with reviewed choices.
4. Break the spec into dependency-ordered sprints, create only the first sprint under
   `.ralph/sprints/`, set `CURRENT_SPRINT`, and validate the complete setup.
5. Tell the operator what to review and stop before running. Invoking `.ralph/loop.sh` starts the
   autonomous loop; do not add or require a redundant authorization boolean.

Do not ask the operator to hand-build `.ralph/` or sprint files. This package exposes one skill,
`$ralph-workflows`; initialization, spec breakdown, sprint creation, chunk design, status, and review
are routed workflows backed by the references below, not separately required skill installations.

## Deterministic runtime

Bootstrap the human interface from the project repository:

```bash
npx zacharygcook/zach-ralph-method
```

The installer delegates to the upstream Skills CLI, which discovers this repository's single skill,
then safely adds the versioned recipe import to a new or existing project `justfile`. For agent-owned
or noninteractive package management, the underlying command is:

```bash
npx skills add zacharygcook/zach-ralph-method
```

The CLI detects the active coding agent and creates a project-local skill copy containing the
instructions, installer, and runtime templates. Use `--agent <name>` only to target a specific agent;
`--agent '*'` deliberately creates adapter copies for every supported client. Run the bundled
`scripts/ralph` launcher from the detected skill directory; it selects Python 3.11+ from either the
`python3` or `python` command.

Prefer `just init`, `just upgrade`, `just validate`, `just status`, `just run`, and `just resume` in
operator-facing instructions. Keep the underlying Skills CLI and fully explicit launcher commands
for agents and automation.

For a repository that already has `skills-lock.json`, refresh the package before upgrading the
project runtime:

```bash
npx skills update ralph-workflows --project
<skill-dir>/scripts/ralph upgrade --repo <repository>
```

Use `npx skills experimental_install` to restore pinned project skills from a committed
lockfile on another machine. `npx skills` owns skill packaging; the bundled runtime command owns
stateful `.ralph/` initialization, migration, validation, and status because the package manager does
not run arbitrary lifecycle hooks.

Install the bundled hardened Bash runtime only when the user asks to initialize or repair Ralph:

```bash
<skill-dir>/scripts/ralph init --repo <repository> --agent <agent> --model '<model>' --reasoning-effort '<effort>' --max-sprint-iterations <sprint-turns> --max-chunk-iterations <chunk-turns> --chunk-validation-command '<fast repo-native command>' --sprint-validation-command '<full repo-native command>'
```

For a parent directory containing independent child Git repositories, use multi-repo mode:

```bash
<skill-dir>/scripts/ralph init --repo <parent> --mode multi-repo --repos <repo-a> <repo-b> --primary-repo <repo-a> --agent <agent> --model '<model>' --reasoning-effort '<effort>' --max-sprint-iterations <sprint-turns> --max-chunk-iterations <chunk-turns> --chunk-validation-command '<fast cross-repo command>' --sprint-validation-command '<full cross-repo command>'
```

Initialization is non-destructive: when `.ralph/` already exists, `init` enters the same safe upgrade
path as `upgrade` and preserves configuration and sprint state. Harness, model, reasoning effort,
sprint turn budget, and per-chunk turn budget are operator choices with no defaults. Interactive initialization and
upgrade prompt for missing choices; noninteractive callers must pass them explicitly. Disable a hook
explicitly when it is genuinely outside the repository's workflow; skipped hooks remain visible in
the manifest.

Upgrade an existing runtime without replacing operator configuration, sprints, logs, or scratchpad
state. Usually the stored validation configuration makes `upgrade --repo <repository>` sufficient.
Legacy `RALPH_TEST_COMMAND` values migrate to the sprint gate; if validation configuration is missing,
supply the commands or explicitly disable the relevant gate:

```bash
<skill-dir>/scripts/ralph upgrade --repo <repository> --chunk-validation-command '<fast repo-native command>' --sprint-validation-command '<full repo-native command>'
```

Validate installed runtime, fingerprints, configuration, and sprint structure with:

```bash
<skill-dir>/scripts/ralph validate --repo <repository>
<skill-dir>/scripts/ralph status --repo <repository>
```

Use `--agent custom --agent-command '<command>'` for another client. The trusted command receives
`RALPH_PROMPT_FILE` and `RALPH_PROJECT_ROOT`. Never place secrets in `config.env`; Bash sources it as
code. Runtime adapters support Codex, Claude Code, Grok Build, Amp, OpenCode, and Factory Droid, but verify the
installed CLI's current flags before a live autonomous run.

A repository may call the same fast command from its existing pre-commit system for earlier feedback.
That hook complements Ralph; it never replaces the independent gate because hooks can be absent,
bypassed, or inappropriate for slow and multi-repository validation. Ralph does not install Husky or
another language-specific hook manager.

## Route the Task

- First use from a spec: [references/first-run.md](references/first-run.md)
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
