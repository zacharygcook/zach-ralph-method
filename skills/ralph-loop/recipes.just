set shell := ["bash", "-uc"]

repo := justfile_directory()
ralph := repo / ".agents/skills/ralph-loop/scripts/ralph"

[default]
[doc('Show Ralph commands')]
help:
    @just --list

[doc('Configure or safely upgrade Ralph interactively')]
init:
    "{{ ralph }}" init --repo "{{ repo }}"

[doc('Update the skill and safely upgrade the runtime')]
upgrade:
    npx skills update ralph-loop ralph-sprint ralph-status ralph-review --project
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

[doc('Select, validate, and run the next prepared sprint')]
next:
    "{{ ralph }}" advance --repo "{{ repo }}"
    "{{ ralph }}" validate --repo "{{ repo }}"
    "{{ repo }}/.ralph/loop.sh"

[doc('Run prepared sprints continuously until work or validation stops')]
marathon: validate
    "{{ repo }}/.ralph/loop.sh" --auto-advance

[doc('Validate and resume an interrupted sprint')]
resume: validate
    "{{ repo }}/.ralph/loop.sh" --resume
