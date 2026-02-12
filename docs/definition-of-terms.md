# Definition of Terms

Key concepts in the Ralph method, precisely defined.

---

## Sprint

A **sprint** is the largest coherent scope of work you'd trust an agent to build autonomously - bounded not by context windows or task count, but by three things:

1. **Coherence**: Can it be reasoned about as a unit? ("Build the data layer" yes, "random backlog items" no)

2. **Definability**: Can you (or the agent) decompose it into chunks? If you can describe it clearly enough to chunk, it's sprintable - regardless of size.

3. **Verifiability**: Can you meaningfully check the output? The verification cost scales with scope, but that's a human bandwidth choice, not a hard limit.

### The Ambition

A sprint is essentially you saying: *"I'm going to let go of the wheel. Build this while I'm not watching."*

The Ralph method's power is that sprints can be **massive** - "build the entire backend," "implement the full pipeline" - as long as the work is coherent and definable. The agent handles decomposition. The agent handles sequencing. The agent handles execution across as many chunks and iterations as needed.

### The Only Real Limits

The limits on sprint scope are human ones:
- Your trust in the agent
- Your patience for verification
- Your tolerance for autonomous runtime

**Not** context windows. Those constrain chunks. Sprints are unbounded upward - limited only by conceptual clarity and your willingness to delegate.

---

## Chunk

A **chunk** is a discrete unit of work completable within a single agent context window.

### Constraints

- **Context-bound**: Must fit in ~200k tokens including code, specs, and conversation
- **Atomic**: Can be completed without human intervention
- **Verifiable**: Has clear acceptance criteria (pass/fail)
- **Sequential**: Ordered by dependencies (FKs, imports, etc.)

### Typical Size

| Chunk Type | Typical Scope |
|------------|---------------|
| Database tables | 3-5 tables |
| API endpoints | 2-4 endpoints |
| UI components | 1-3 complex components |
| Bug fixes | 1-3 related fixes |

### Key Distinction

Chunks are limited by context windows. Sprints are not. A sprint can contain unlimited chunks - the only requirement is that each individual chunk fits in context.

---

## Iteration

An **iteration** is a single run of the agent within the loop.

- Agent receives prompt
- Agent works until it exits (completion, blocked, or timeout)
- Loop checks for signals (`RALPH_COMPLETE`, `<blocked>`)
- Loop commits progress and continues (or stops)

One chunk may take multiple iterations. One iteration may complete a chunk. The relationship is flexible.

---

## The Loop

The **loop** is the bash script that orchestrates autonomous execution:

```
┌─────────────────────────────────────┐
│         while chunks remain         │
│  ┌───────────────────────────────┐  │
│  │  1. Inject prompt             │  │
│  │  2. Agent executes            │  │
│  │  3. Check completion signal   │  │
│  │  4. Commit progress           │  │
│  │  5. Continue or exit          │  │
│  └───────────────────────────────┘  │
└─────────────────────────────────────┘
```

The loop's job is persistence across context resets. Files survive. Git commits survive. Progress accumulates even as agent context resets between iterations.

---

## RALPH_COMPLETE

The completion signal: `<promise>RALPH_COMPLETE</promise>`

When the agent outputs this, it signals:
- Current chunk's acceptance criteria are met
- chunks.json has been updated (`passes: true`)
- Work has been committed to git
- Ready for next chunk (or sprint complete)

---

## Blocked

The stuck signal: `<blocked>Reason here</blocked>`

When the agent outputs this, it signals:
- Cannot proceed without human input
- Loop should exit for human intervention
- Reason is logged for debugging

Examples:
- Missing API credentials
- Ambiguous requirements
- External dependency unavailable

---

## Scratchpad

The **scratchpad** (`SCRATCHPAD.md`) is a per-sprint file that persists "negative knowledge" across context resets — dead ends, gotchas, non-obvious decisions, and debugging insights that would otherwise be lost when the loop starts a fresh iteration.

Agents read the scratchpad first (before any other sprint file) and append learnings last (before outputting RALPH_COMPLETE). This creates a persistent memory layer that compensates for context window resets.

**What belongs in the scratchpad**:
- Approaches that were tried and rejected (and why)
- Non-obvious ordering dependencies
- API quirks or framework gotchas discovered during implementation
- Where a WIP iteration left off

**What doesn't belong**: Implementation plans (that's `IMPLEMENTATION_PLAN.md`), acceptance criteria (that's `chunks.json`), or code documentation.

---

## Trust Boundary

A **trust boundary** is the scope within which you're comfortable with autonomous execution.

Sprints are trust boundaries. You're saying: "I trust the agent to handle everything within this sprint without asking me."

Trust boundaries are personal and contextual:
- Early in a project: smaller sprints, more verification
- Established patterns: larger sprints, more delegation
- Critical systems: tighter boundaries regardless of experience

---

## Context Window vs. Sprint Scope

A common misconception: sprint size is limited by context windows.

**Reality:**
- **Context windows limit chunks** - each chunk must fit
- **Sprints have no context limit** - they're organizational units
- A sprint can be arbitrarily large if it can be decomposed into chunks

The agent's context resets between iterations, but progress persists in files and git. This is the core insight that enables large sprints.
