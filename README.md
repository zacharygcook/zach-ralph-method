# The Ralph Method

A hardened, observable autonomous coding loop for one repository or a coordinated group of repositories.

Ralph gives a coding agent a bounded chunk of work, lets it implement and verify that chunk in a fresh context, records durable handoff state, and repeats. The runtime treats autonomy as an operator-controlled capability: it installs disarmed, fingerprints its managed files, validates real state changes before accepting completion, and leaves interrupted post-sprint work resumable.

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
- **Operator-owned safety.** Unattended execution and broad automatic staging have separate, explicit authorization gates. Both default off.
- **Crash-safe orchestration.** Manifests, locks, heartbeats, structured events, state files, and `--resume` make long runs inspectable and recoverable.
- **First-class multi-repo work.** Each child repository keeps its own Git boundary and start/end commit range.
- **Project-neutral hooks.** Review, documentation, test, and E2E commands are configured by the adopting project rather than assumed by the runtime.

## Install in 30 seconds

From the Git repository you want Ralph to manage, vendor the complete private skill with the Skills
CLI. Your local GitHub credentials must have access to `zach-ralph-method`:

```bash
npx skills@latest add zacharygcook/zach-ralph-method --skill ralph-workflows --copy -y
```

Confirm the project-local installation:

```bash
npx skills@latest list
```

The Skills CLI detects the active coding agent. Pass `--agent <name>` only when targeting one
explicitly; `--agent '*'` intentionally installs copies for every supported client.

### What `npx skills` manages

Ralph has two deliberately separate layers:

| Layer | Use | Why |
| --- | --- | --- |
| Skill package | `npx skills add`, `update`, `list`, `remove`, and `experimental_install` | Vendor and refresh instructions, scripts, and templates without a manual clone. |
| Project runtime | Bundled `ralph.py` and `.ralph/loop.sh` | Safely initialize, migrate, validate, inspect, and run repository-owned state. |

`npx skills` is the primary package manager. It intentionally does not execute arbitrary
post-install hooks, so the bundled Python command remains necessary when creating or migrating the
stateful `.ralph/` runtime.

### Initialize a new project

After the `npx skills add` command, initialize from the vendored copy:

```bash
python3 .agents/skills/ralph-workflows/scripts/ralph.py init --repo . --agent codex --chunk-validation-command "your fast check" --sprint-validation-command "your full check"
```

The installer creates `.ralph/` but leaves autonomous execution disarmed. Review
`.ralph/config.env`, create a sprint, then explicitly set `RALPH_UNATTENDED_APPROVED=true` only when
you are ready.

### Update an existing project

Refresh the vendored skill first, then safely migrate its generated runtime:

```bash
npx skills@latest update ralph-workflows --project -y
python3 .agents/skills/ralph-workflows/scripts/ralph.py upgrade --repo .
```

The upgrade preserves configuration, authorization, sprints, logs, and scratchpads. A legacy runtime
without validation gates stops and requests the missing commands instead of guessing them.

### Restore skills from a committed lockfile

When a repository already contains `skills-lock.json`, restore its pinned project skills with:

```bash
npx skills@latest experimental_install
```

The command name is currently marked experimental by the Skills CLI; the committed lockfile remains
the reproducible source declaration.

## Quick start

Every sprint lives at `.ralph/sprints/<number-name>/` and contains:

```text
README.md                short goal and boundaries
IMPLEMENTATION_PLAN.md   ordered implementation design
relevant-specs.md        curated source-of-truth context
chunks.json              sequential work and acceptance criteria
prompt.md                instructions for each fresh agent context
SCRATCHPAD.md            append-only discoveries and handoff memory
```

Set `CURRENT_SPRINT` in `.ralph/config.env`, then:

```bash
python3 .agents/skills/ralph-workflows/scripts/ralph.py validate --repo .
./.ralph/loop.sh
python3 .agents/skills/ralph-workflows/scripts/ralph.py status --repo .
```

Use `.ralph/loop.sh --resume` after interruption. Use `--force-hooks` only when intentionally rerunning completed post-sprint hooks.

## Supported agent harnesses

The generated runtime supports Claude Code, Codex, Droid, Amp, OpenCode, and a trusted custom command. CLI flags evolve, so `RALPH_AGENT_COMMAND` provides an escape hatch without changing the orchestrator.

Custom commands receive:

- `RALPH_PROMPT_FILE` — the prompt file for the current iteration or hook
- `RALPH_PROJECT_ROOT` — the working directory the command should use

## Safety model

The default installation will not run autonomously. It also will not auto-commit. A project must set
`RALPH_AUTO_COMMIT=I_ACCEPT_GIT_ADD_ALL` to deliberately enable broad backup commits. Normal agent
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

## Validation and portability

```bash
python3 -m unittest discover -s tests -v
```

The clean-room suite installs and executes disposable monorepo and multi-repo fixtures. GitHub Actions runs it on macOS and Linux with multiple Python versions.

To develop Ralph itself instead of consuming it as a skill, clone this repository and use the
canonical `scripts/ralph.py`. Normal adopting projects should prefer `npx skills` and the vendored
copy documented above.

## Documentation

- [`docs/sprint-structure.md`](docs/sprint-structure.md) — sprint anatomy and lifecycle
- [`docs/multi-repo-setup.md`](docs/multi-repo-setup.md) — coordinating independent repositories
- [`docs/definition-of-terms.md`](docs/definition-of-terms.md) — precise vocabulary
- [`docs/migration-report.md`](docs/migration-report.md) — hardening history

## Credits

Inspired by [Geoffrey Huntley's Ralph technique](https://ghuntley.com/ralph/), [frankbria/ralph-claude-code](https://github.com/frankbria/ralph-claude-code), and [vercel-labs/ralph-loop-agent](https://github.com/vercel-labs/ralph-loop-agent).
