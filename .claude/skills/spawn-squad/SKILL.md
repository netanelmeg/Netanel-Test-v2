---
name: spawn-squad
description: Fan work out to a squad of specialized subagents (architect, builder, reviewer, tester) using a mission contract with verifiable success criteria. Use for work too large, too parallel, or too risky for a single pass — multi-file features, migrations, or anything needing independent verification.
---

# Spawn Squad

Adapted for Claude Code: the squad members are **subagents invoked with the `Agent` tool**, defined in `.claude/agents/`. There is no separate CLI and no separate workspace per member — they run in this session, against this repo.

## The squad

| Agent | Role | Writes code? |
|---|---|---|
| `architect` | Explores the code, returns a file-level plan with success criteria | No |
| `builder` | Executes a settled plan | Yes |
| `reviewer` | Independent correctness/security review of the diff | No |
| `tester` | Runs build/tests/lint, reports evidence | No |

Invoke one with the `Agent` tool, setting `subagent_type` to the agent's name.

## When to spawn — and when not to

**Spawn when:**
- The task spans many files or subsystems
- Independent verification matters (the reviewer must not be the author)
- Several parts are genuinely parallel — separate modules, separate hypotheses
- You want a plan critiqued before any code is written

**Don't spawn when:**
- The task fits in a single pass — just do it, spawning is pure overhead
- Success criteria don't exist yet — define them first, or the result can't be judged
- The subagents would need to edit the same files concurrently — they'll clobber each other

## Step 0 — Write the mission contract

Non-negotiable. Before invoking anyone, write down:

```markdown
**Objective:** {one sentence}
**Scope:** {in bounds / out of bounds}
**Success criteria:**
- [ ] {verifiable — "gradlew build exits 0", "src/api/routes.ts exports a Router"}
**Forbidden:** {e.g. don't touch CI config, don't push, don't add dependencies}
**Stop condition:** {e.g. after 2 failed attempts, report FAIL with diagnostics}
```

If you can't write concrete success criteria, you don't understand the task well enough to delegate it.

## Step 1 — Brief the subagent properly

A subagent starts **cold**. It has not seen this conversation, doesn't know what you've tried, and can't ask a follow-up. A terse prompt produces shallow work.

Every prompt must carry:
- What you're trying to accomplish, and why
- What you already know or have ruled out
- Exact file paths and line numbers where you have them
- The success criteria from the contract
- The output shape you expect back

**Never delegate the thinking.** "Based on your findings, fix it" pushes synthesis onto an agent with less context than you. Say what to change and where.

## Step 2 — Sequence or parallelize

**Sequential** (the common case — each stage feeds the next):
```
architect → builder → tester → reviewer
```

**Parallel** — only for genuinely independent work. Send one message with multiple `Agent` calls:
- Several read-only investigations (safe: nothing writes)
- Builders scoped to strictly disjoint file sets

**Isolation rule:** never run two writing agents over the same files at once. Read-only agents parallelize freely; writers need disjoint scopes or must run in sequence.

## Step 3 — Verify independently

**Do not trust a subagent's summary.** It describes what the agent *intended*, not necessarily what it did. Verify yourself:

```bash
git status --porcelain          # what actually changed?
git diff                        # is the change what was described?
{the project's build/test cmd}  # does it actually pass?
```

Check every success criterion from the contract. An unverified criterion is a failed one.

## Step 4 — Record the verdict

```markdown
**Result:** PASS | PARTIAL | FAIL
**Criteria:** {n}/{total} met — {which one failed, and why}
**Changed:** {files}
**Notes:** {deviations, retries, anything unresolved}
```

## Anti-patterns

- **Spawning without a contract.** No criteria means no way to tell success from a confident-sounding failure.
- **Trusting the report over the repo.** Always `git diff`.
- **Parallel writers on shared files.** Guaranteed lost work.
- **Spawning for trivial tasks.** Each subagent starts cold and re-derives context you already have — that's the expensive path.
- **Unbounded fan-out.** Start with 2–3 and scale only after the pattern proves out.
- **The author reviewing their own work.** The point of a separate `reviewer` is that it hasn't seen the reasoning that produced the bug.
