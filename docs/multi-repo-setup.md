# Multi-Repo Setup Guide

Guide for using Ralph with projects that have separate API and Frontend repositories.

## When to Use Multi-Repo Mode

Use this when:
- API and Frontend are in separate git repos
- You want Ralph to orchestrate work across both
- Changes often need to be coordinated between repos

## Directory Structure

```
project-parent/           # NOT a git repo
├── .ralph/               # Ralph lives here
│   ├── config.env        # REPOS="api frontend", timeouts
│   ├── loop.sh           # Hardened loop (heartbeat, state-delta)
│   ├── status.sh         # Operator status command
│   ├── lib/
│   │   └── ralph-common.sh  # Shared helpers (locking, events)
│   ├── hooks/
│   ├── prompts/
│   ├── logs/
│   └── sprints/
├── api/                  # Separate git repo
│   ├── .git/
│   └── CLAUDE.md
├── frontend/             # Separate git repo
│   ├── .git/
│   └── CLAUDE.md
└── CLAUDE.md             # Parent overview
```

## Setup Steps

### 1. Create Parent Directory

```bash
mkdir my-project
cd my-project
```

### 2. Clone or Move Repos

```bash
# Clone existing repos
git clone git@github.com:you/api.git
git clone git@github.com:you/frontend.git

# Or move existing directories
mv /path/to/api ./
mv /path/to/frontend ./
```

### 3. Run Ralph Init

```bash
/ralph-init
# Select: Multi-repo
# Enter repo names: api frontend
```

### 4. Verify Structure

```bash
ls -la
# Should see: .ralph/  api/  frontend/  CLAUDE.md

ls -la .ralph/
# Should see: config.env  loop.sh  sprints/  hooks/  ...
```

## Configuration

### config.env

```bash
AGENT=claude
MAX_ITERATIONS=30
CURRENT_SPRINT=1-initial-setup

# Multi-repo settings
REPOS="api frontend"
PRIMARY_REPO=api
```

### chunks.json

Chunks have a `repo` field:

```json
{
  "chunks": [
    {
      "id": 1,
      "title": "Add user endpoint",
      "repo": "api",
      "artifacts": ["src/routes/user.ts"],
      "acceptance_criteria": ["..."],
      "passes": false
    },
    {
      "id": 2,
      "title": "Add user page",
      "repo": "frontend",
      "depends_on": [1],
      "artifacts": ["src/pages/user.tsx"],
      "acceptance_criteria": ["..."],
      "passes": false
    },
    {
      "id": 3,
      "title": "Connect auth flow",
      "repo": "both",
      "artifacts": {
        "api": ["src/middleware/auth.ts"],
        "frontend": ["src/hooks/useAuth.ts"]
      },
      "acceptance_criteria": ["..."],
      "passes": false
    }
  ]
}
```

### manifest.json

Tracks commits per-repo and sprint lifecycle:

```json
{
  "sprint": "1-initial-setup",
  "phase": "running",
  "repos": {
    "api": {
      "start_commit": "abc123",
      "end_commit": null
    },
    "frontend": {
      "start_commit": "def456",
      "end_commit": null
    }
  },
  "hooks": {
    "review": { "status": "pending" },
    "documentation": { "status": "pending" },
    "tests": {
      "status": "pending",
      "phases": {
        "generate_tests": { "status": "pending" },
        "verify_backend_tests": { "status": "pending" },
        "run_e2e": { "status": "pending" }
      }
    }
  },
  "commits": [
    {
      "chunk_id": 1,
      "iteration": 2,
      "repos": {
        "api": "abc124",
        "frontend": null
      }
    }
  ]
}
```

## Git Operations

**Critical:** Always `cd` into the repo before git commands.

```bash
# API changes
cd api && git add -A && git commit -m "feat: add user endpoint"

# Frontend changes
cd frontend && git add -A && git commit -m "feat: add user page"

# Both repos
cd api && git add -A && git commit -m "feat: auth integration (api)"
cd ../frontend && git add -A && git commit -m "feat: auth integration (frontend)"
```

**Never run git from the parent directory** - there's no .git there.

## Prompt Template

The multi-repo prompt.md includes:

```markdown
## Multi-Repo Project Structure

You are working in a multi-repo project:
- Parent: /path/to/project (contains .ralph/, NO .git)
- API: /path/to/project/api (has its own .git)
- Frontend: /path/to/project/frontend (has its own .git)

## Git Operations

IMPORTANT: Always cd into the correct repo before git commands:
- API changes: `cd api && git add -A && git commit -m "..."`
- Frontend changes: `cd frontend && git add -A && git commit -m "..."`
```

## Post-Sprint Hooks

Hooks are adapted for multi-repo:

| Hook | Multi-Repo Behavior |
|------|---------------------|
| `review.sh` | Aggregates diffs from all repos |
| `test.sh` | Runs tests in each modified repo |
| `document.sh` | Updates CLAUDE.md in each repo |

## Tips

### Docker Compose

If each repo has its own docker-compose:

```bash
# Start all services
cd api && docker compose up -d
cd ../frontend && docker compose up -d
```

### Type Sharing

If you need shared types between repos:
- Option 1: Duplicate and manually sync
- Option 2: Create a shared npm package
- Option 3: Use API-generated types (OpenAPI, GraphQL codegen)

### Branch Strategy

Keep branches in sync across repos:
```bash
# Create feature branch in both
cd api && git checkout -b feature-x
cd ../frontend && git checkout -b feature-x
```

## Troubleshooting

### "Not a git repository" error

You're probably running git from the parent. Always `cd` into the repo first.

### Commits not tracked in manifest

Check that:
- Agent is committing from within repo directories
- manifest.json has correct repo names in `repos` object

### Hooks failing

Verify:
- REPOS is set correctly in config.env
- Each repo directory exists and has .git

## Example Workflow

```bash
# 1. Set up project
mkdir lead-getter && cd lead-getter
git clone git@github.com:you/lead-getter-api.git api
git clone git@github.com:you/lead-getter-frontend.git frontend

# 2. Initialize Ralph
/ralph-init  # Select multi-repo

# 3. Create sprint with GOAL.md
cat > GOAL.md << 'EOF'
# Goal: Add lead import feature

## Problem
Users need to bulk import leads from CSV.

## Success Criteria
- [ ] API endpoint accepts CSV upload
- [ ] Frontend has upload UI
- [ ] Validation errors shown to user

## Scope
- Repos: both
EOF

# 4. Create implementation plan and chunks
# (use /ralph-chunk for help)

# 5. Run the loop
./.ralph/loop.sh
```
