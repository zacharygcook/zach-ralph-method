set shell := ["bash", "-uc"]

repo := justfile_directory()
ralph := repo / ".agents/skills/ralph-workflows/scripts/ralph"

[default]
[doc('Show Ralph commands')]
help:
    @just --list

[doc('Configure or safely upgrade Ralph interactively')]
init:
    "{{ ralph }}" init --repo "{{ repo }}"

[doc('Update the skill and safely upgrade the runtime')]
upgrade:
    npx skills update ralph-workflows --project
    "{{ ralph }}" upgrade --repo "{{ repo }}"

[doc('Validate runtime, configuration, and sprint state')]
validate:
    "{{ ralph }}" validate --repo "{{ repo }}"

[doc('Show current sprint progress')]
status:
    "{{ ralph }}" status --repo "{{ repo }}"

[doc('Validate and start the current sprint')]
run: validate
    "{{ repo }}/.ralph/loop.sh"

[doc('Validate and resume an interrupted sprint')]
resume: validate
    "{{ repo }}/.ralph/loop.sh" --resume
