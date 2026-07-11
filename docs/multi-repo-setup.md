# Multi-repo setup

Use multi-repo mode when one unit of work spans two or more independent Git repositories under a shared parent directory.

## Layout

```text
product/
├── .ralph/       orchestration state; installed here
├── service/      independent Git repository
├── dashboard/    independent Git repository
└── mobile/       optional additional Git repository
```

Repository names are configuration, not conventions. The parent directory does not need to be a Git repository.

## Install

Vendor the skill from the shared parent directory first:

```bash
npx skills@latest add zacharygcook/zach-ralph-method --skill ralph-workflows --copy -y
```

Then initialize the parent runtime from the vendored package:

```bash
python3 .agents/skills/ralph-workflows/scripts/ralph.py init --repo /path/to/product --mode multi-repo --repos service dashboard mobile --primary-repo service --agent codex --model "your model" --chunk-validation-command "your fast validation command" --sprint-validation-command "your full validation command"
```

The installer verifies every named child contains `.git`, records the topology in `.runtime-manifest.json`, and writes `RALPH_REPOS` plus `RALPH_PRIMARY_REPO` to `config.env`.

## Chunk ownership

Each chunk adds a `repo` field naming one configured child repository. Use `all` for work spanning every configured repository; `both` remains supported for two-repository sprint files.

```json
{
  "chunks": [
    {
      "id": 1,
      "title": "Publish the contract",
      "repo": "service",
      "artifacts": ["openapi.json"],
      "acceptance_criteria": ["The generated contract is current"],
      "passes": false
    },
    {
      "id": 2,
      "title": "Consume the contract",
      "repo": "dashboard",
      "artifacts": ["src/generated/api.ts"],
      "acceptance_criteria": ["The client compiles against the new contract"],
      "passes": false
    }
  ]
}
```

The validator rejects unknown repository owners before execution.

## Git boundaries

Agents commit within each changed child repository, using `git -C <name>` or changing into that directory. They inspect status and stage only chunk-owned paths. A cross-repository chunk is not complete until every affected repository meets its acceptance criteria and has its own coherent commit.

The manifest records `start_commit` and `end_commit` separately per repository. Review hooks receive every repository's exact sprint range, preventing a single-repo diff from hiding half of a coordinated change.

## Project commands

The runtime does not guess languages, package managers, services, or test frameworks. Configure
`RALPH_CHUNK_VALIDATION_COMMAND`, `RALPH_SPRINT_VALIDATION_COMMAND`, optional `RALPH_E2E_COMMAND`,
and hook agents in `.ralph/config.env`. Commands run from the shared parent so they can coordinate
services when necessary. A named-repository chunk requires a new commit there; `all`/`both` chunks
require commit evidence from every configured child repository.

## Validate and operate

```bash
python3 .agents/skills/ralph-workflows/scripts/ralph.py validate --repo /path/to/product
/path/to/product/.ralph/loop.sh
python3 .agents/skills/ralph-workflows/scripts/ralph.py status --repo /path/to/product
```

Status shows each child repository's commit range, hook state, latest events, and heartbeat age using portable Python timestamp parsing on macOS and Linux.
