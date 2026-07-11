# The Ralph Method

A hardened, observable autonomous coding loop for one repository or a coordinated group of repositories.

Ralph gives a coding agent a bounded chunk of work, lets it implement and verify that chunk in a fresh context, records durable handoff state, and repeats. The runtime makes autonomy inspectable: it requires an explicit harness and model, enforces sprint and per-chunk turn budgets, fingerprints managed files, validates real state changes before accepting completion, and leaves interrupted post-sprint work resumable.

```text
SPEC → PLAN → CHUNKS → IMPLEMENT → VERIFY → COMMIT
                         ↑                    │
                         └── fresh context ───┘
                                  │
                           all chunks pass
                                  ↓
                        REVIEW → DOCS → TESTS
```

## Why this implementation

- **Fresh context, durable memory.** Each iteration starts a new agent process and reads `SCRATCHPAD.md`, plans, specs, and chunk state from disk.
- **Evidence-backed completion.** A completion marker counts only when the number of passing chunks increases.
- **Operator-owned controls.** Harness, model, sprint turn budget, per-chunk turn budget, and validation are explicit. Broad automatic staging remains separately gated and defaults off.
- **Crash-safe orchestration.** Manifests, locks, heartbeats, structured events, state files, and `--resume` make long runs inspectable and recoverable.
- **First-class multi-repo work.** Each child repository keeps its own Git boundary and start/end commit range.
- **Project-neutral hooks.** Review, documentation, test, and E2E commands are configured by the adopting project rather than assumed by the runtime.

## Install in 30 seconds

Install [`just`](https://just.systems) with your package manager:

```bash
brew install just                         # macOS
sudo apt install just                     # Ubuntu / Debian
sudo pacman -S just                       # Arch Linux
winget install --id Casey.Just --exact    # Windows
```

From the Git repository you want Ralph to manage:

```bash
npx zacharygcook/zach-ralph-method
```

The installer vendors the repository's single skill and safely adds its recipes to an existing or
new project `justfile`. Then initialize interactively:

```bash
just init
```

The setup asks for the harness, exact model, sprint and per-chunk turn budgets, fast chunk validation,
and comprehensive sprint validation. It does not guess operator choices.

### Everyday commands

```bash
just init       # configure a new or existing runtime
just upgrade    # update the skill and runtime safely
just validate   # check readiness without running
just status     # inspect the current sprint
just run        # validate, then start
just resume     # validate, then resume
```

Run `just` by itself to see the command list. The root `justfile` imports versioned recipes from the
vendored skill, so `just upgrade` refreshes commands without replacing your project file.

### Restore skills from a committed lockfile

When a repository already contains `skills-lock.json`, restore its pinned project skills with:

```bash
npx skills experimental_install
```

The command name is currently marked experimental by the Skills CLI; the committed lockfile remains
the reproducible source declaration.

## Quick start: from a spec to a running loop

### 1. Check the prerequisites

Before the first sprint, have:

- A Git repository with a known baseline and no unexplained concurrent changes.
- Node.js/npm with `npx`, plus `just`, for installing and operating the skill.
- Bash, Git, `jq`, and Python 3 for the generated runtime.
- A supported coding-agent CLI: Codex, Claude Code, Droid, Amp, OpenCode, or a configured custom command.
- A durable `SPEC.md` (or equivalent source of truth) describing the desired system and boundaries.
- One fast per-chunk validation command and one comprehensive final validation command. Existing test,
  lint, typecheck, build, and E2E scripts are ideal inputs.

On Windows, run the Bash runtime in a compatible environment such as WSL. If the repository does
not have a useful spec or validation commands yet, create those before starting a loop.

### 2. Ask the skill to prepare the first sprint

This repository ships one operator-facing skill: `$ralph-workflows`. The initialization, spec
breakdown, sprint creation, chunk planning, status, and review workflows are bundled references—not
separate skills you need to install or memorize.

Ask your coding agent:

```text
Use $ralph-workflows to preflight this repository for a Ralph loop. Read SPEC.md and the repository's
agent instructions. Identify the fast chunk-validation command and comprehensive sprint-validation
command. Confirm the harness, exact model, maximum sprint turns, and maximum turns per chunk with me.
Initialize or upgrade .ralph, break the spec into dependency-ordered sprints, create only the first
sprint, set CURRENT_SPRINT, validate the complete setup, and stop before running. Explain any blockers
and summarize exactly what I should review.
```

You do **not** manually create `.ralph/` or its sprint files. The deterministic installer creates the
runtime directories; the skill creates `.ralph/sprints/<number-name>/`, curates the relevant spec,
builds `chunks.json`, adds persistent `SCRATCHPAD.md` memory, and selects the active sprint.

### 3. Review before arming

Inspect the proposed sprint, especially its goal, chunk order, artifacts, acceptance criteria, and
validation commands. To ask the skill for a readiness check:

```text
Use $ralph-workflows to inspect the current Ralph sprint and tell me whether it is safe and complete
enough to run. Confirm the configured harness, model, sprint turn budget, and per-chunk turn budget.
Do not start the loop.
```

The current sprint lives at the path named by `CURRENT_SPRINT` in `.ralph/config.env`. Every sprint
contains `README.md`, `IMPLEMENTATION_PLAN.md`, `relevant-specs.md`, `chunks.json`, `prompt.md`, and
`SCRATCHPAD.md`.

### 4. Confirm and run deliberately

After reviewing `.ralph/config.env`, run:

```bash
just run
```

Inspect progress at any time with:

```bash
just status
```

Use `just resume` after interruption. Use the automation interface below only when intentionally
rerunning completed post-sprint hooks.

### Which workflow should I ask for?

| Goal | Ask `$ralph-workflows` to… |
| --- | --- |
| First use | Preflight prerequisites, initialize `.ralph`, plan sprints, and create the first sprint without arming it. |
| Existing installation | Update/upgrade safely, validate fingerprints and configuration, and preserve sprint state. |
| New or changed spec | Break the spec into dependency-ordered sprints and prepare only the next sprint. |
| Sprint design | Create or validate the sprint files, chunks, acceptance criteria, artifacts, and scratchpad. |
| Progress check | Report real status from chunks, manifest phase, hooks, markers, and logs. |
| Completion review | Check spec alignment and confirm that implementation plus required hooks actually finished. |

## Supported agent harnesses

The generated runtime supports Claude Code, Codex, Droid, Amp, OpenCode, and a trusted custom
command. The selected model is never implicit:

| Harness | `RALPH_AGENT_MODEL` meaning |
| --- | --- |
| Claude Code, Codex, Droid | Exact value passed through `--model`. |
| OpenCode | Provider/model value passed through `--model`. |
| Amp | Amp mode passed through `--mode` (`deep`, `free`, `large`, `rush`, or `smart`). |
| Custom command | Exported as `RALPH_AGENT_MODEL`; the command owns how to use it. |

CLI flags evolve, so adapter argument construction is regression-tested and `RALPH_AGENT_COMMAND`
provides an immediate escape hatch without changing the orchestrator.

Custom commands receive:

- `RALPH_PROMPT_FILE` — the prompt file for the current iteration or hook
- `RALPH_PROJECT_ROOT` — the working directory the command should use

## Safety model

Running `.ralph/loop.sh` is the operator's decision to start the autonomous loop; there is no second
boolean that restates that intent. Before launching, validation requires an available explicitly
selected harness, explicit model, positive explicitly selected sprint and per-chunk turn budgets,
and configured validation commands. Neither installation nor the Bash runtime guesses those
operator decisions.

The runtime does not auto-commit broadly. A project must set
`RALPH_AUTO_COMMIT=I_ACCEPT_GIT_ADD_ALL` to deliberately enable broad backup commits; normal agent
prompts instruct scoped staging instead.

The migration-aware upgrade refreshes only managed runtime files. It preserves operator
configuration, sprints, logs, and scratchpad state, promotes legacy validation configuration, and
refuses mode changes or managed symlinks that could escape `.ralph/`.

## Evidence-gated completion

An agent's completion marker is a candidate, not proof. Ralph accepts exactly one next sequential
chunk per iteration, reruns `RALPH_CHUNK_VALIDATION_COMMAND`, and requires a new commit in the
chunk-owned repository or repositories. Failed validation resets only that chunk to `passes: false`,
records the attempt and log in the manifest, and adds a repair handoff to `SCRATCHPAD.md`.

After review and documentation hooks finish, `RALPH_SPRINT_VALIDATION_COMMAND` verifies the actual
final repository state; optional E2E runs last. A repository may call the same fast command from a
pre-commit hook for earlier feedback, but Ralph's independent gate remains authoritative.

## Automation interface

Agents and scripts can bypass the interactive recipes by passing every decision explicitly:

```bash
./.agents/skills/ralph-workflows/scripts/ralph init --repo . --agent "your harness" --model "your model" --max-sprint-iterations "your sprint budget" --max-chunk-iterations "your chunk budget" --chunk-validation-command "your fast check" --sprint-validation-command "your full check"
./.agents/skills/ralph-workflows/scripts/ralph upgrade --repo .
./.agents/skills/ralph-workflows/scripts/ralph validate --repo .
./.ralph/loop.sh --resume
./.ralph/loop.sh --force-hooks
```

## Validation and portability

```bash
python3 -m unittest discover -s tests -v
```

The clean-room suite installs and executes disposable monorepo and multi-repo fixtures. GitHub Actions runs it on macOS and Linux with multiple Python versions.

To develop Ralph itself instead of consuming it as a skill, clone this repository and use the
canonical `scripts/ralph` launcher. Normal adopting projects should prefer `npx skills` and the vendored
copy documented above.

## Documentation

- [`docs/sprint-structure.md`](docs/sprint-structure.md) — sprint anatomy and lifecycle
- [`docs/multi-repo-setup.md`](docs/multi-repo-setup.md) — coordinating independent repositories
- [`docs/definition-of-terms.md`](docs/definition-of-terms.md) — precise vocabulary
- [`docs/migration-report.md`](docs/migration-report.md) — hardening history

## Credits

Inspired by [Geoffrey Huntley's Ralph technique](https://ghuntley.com/ralph/), [frankbria/ralph-claude-code](https://github.com/frankbria/ralph-claude-code), and [vercel-labs/ralph-loop-agent](https://github.com/vercel-labs/ralph-loop-agent).
