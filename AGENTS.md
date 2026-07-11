# Ralph Method — Agent Guide

This repository packages a hardened autonomous coding loop for one Git repository or a parent directory containing multiple child repositories.

## Before changing the runtime

- Read `README.md`, the relevant guide under `docs/`, and the templates you will change.
- Preserve disarmed defaults: unattended execution requires `RALPH_UNATTENDED_APPROVED=true`; automatic broad staging requires the separate `I_ACCEPT_GIT_ADD_ALL` sentinel.
- Never make a particular language, package manager, test framework, repository name, or branch part of the generic runtime.
- Keep monorepo and multi-repo behavior aligned unless their Git topology requires a real difference.
- Keep `AGENTS.md` and `CLAUDE.md` identical.

## Validation

Run `python3 -m unittest discover -s tests -v`. The suite installs the runtime into disposable Git repositories and exercises safety gates, validation rejection and repair, commit evidence, drift detection, resumable hooks, and both repository modes.

Run `python3 scripts/ralph.py --help` to inspect the public CLI. Shell templates must pass `bash -n` and remain portable across current macOS and Linux Bash environments.

## Runtime contract

- `.ralph/config.env` is operator-owned after installation; `--update-runtime` must preserve it and all sprint state.
- `.ralph/.runtime-manifest.json` fingerprints managed runtime files and records the installation mode.
- Every sprint reads and updates `SCRATCHPAD.md` so fresh agent contexts inherit durable state.
- Completion signals are accepted only when chunk state actually advances.
- Exactly one next sequential chunk may advance, and repository-native validation plus commit evidence must pass before acceptance.
- Disabled hooks are explicit successful skips; failed or interrupted hooks remain resumable.
- Multi-repo manifests record start and end commits separately for every configured child repository.

Use scoped commits and never sweep unrelated working-tree changes into runtime work.
