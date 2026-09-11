---
name: github-distributed-coordination
description: Use GitHub itself (issue comments, labels, timestamps) as the coordination backend so multiple agents or machines can claim work without duplicating effort — with lease expiry and automatic recovery. Use when several concurrent agents share one issue board.
---

# GitHub-Native Distributed Coordination

> **The `gh` commands below do not run in Claude Code on the web.** That environment has **no `gh` CLI** (verified: `command -v gh` returns nothing). The coordination *pattern* still holds — only the transport changes. Translate before use:
>
> | `gh` command | MCP equivalent |
> |---|---|
> | `gh issue comment` | `mcp__github__add_issue_comment` |
> | `gh issue view` | `mcp__github__issue_read` |
> | `gh issue edit --add-label` | `mcp__github__issue_write` (method `update`) — see warning |
> | `gh issue list --label` | `mcp__github__list_issues` (`labels` filter) |
>
> Load the exact schemas with `ToolSearch` before calling — argument shapes differ from the CLI flags.
>
> ⚠️ **Label handling differs and will bite you.** `gh issue edit` has incremental `--add-label` / `--remove-label`; `issue_write` takes a **whole `labels` array that replaces the existing set**. Translating the claim/release steps naively will silently wipe every other label on the issue. Read the current labels first (`issue_read` method `get_labels`), then write back the full array with your `machine:*:active` entry added or removed.

## Context

When multiple autonomous agents or processes need to divide work without duplicating effort, **GitHub can be the coordination backend** using native features (comments, labels, timestamps) instead of external infrastructure (Redis, a database, a message queue).

This gives distributed work claiming with automatic recovery, zero new infrastructure, and a complete audit trail.

## Use Cases

✅ **Good fit for:**
- Multiple agents working the same issue board
- Distributed job processors claiming tasks from GitHub issues
- Automated workflows needing failover (process crashes, network loss)
- Anything requiring a who-did-what-when audit trail

❌ **Not suitable for:**
- High-frequency coordination (>100 ops/min) — API rate limits
- Real-time locking (<1s latency) — API roundtrip is 1–3s
- Large-scale coordination (>1000 concurrent workers)
- Safety-critical systems requiring guaranteed consistency

## Architecture Pattern

### 1. Worker Identity

Each process identifies itself with a stable, unique ID:

```bash
worker_id="${WORKER_ID:-$(hostname | tr -c 'a-zA-Z0-9-' '-')}"
```

### 2. Work Claiming Protocol

Claim by posting a comment — the comment itself is the lock record:

These snippets use GNU `date` (`date -u -d`). On macOS/BSD, install coreutils and use `gdate`, or parse with `date -j -f`.

```bash
claim_work() {
  local issue="$1" worker="$2" lease_minutes="${3:-15}"

  # Look at the most recent claim, if any
  local existing
  existing=$(gh issue view "$issue" --json comments \
    --jq '[.comments[] | select(.body | test("Claimed by")) ] | last | .body // ""')

  if [[ -n "$existing" && "$existing" != *"Claimed by $worker"* ]]; then
    local claimed_at age_min
    claimed_at=$(sed -n 's/.*at \([0-9TZ:-]*\).*/\1/p' <<<"$existing")
    age_min=$(( ( $(date -u +%s) - $(date -u -d "$claimed_at" +%s) ) / 60 ))
    (( age_min < lease_minutes )) && return 1   # still leased by someone else
  fi

  local ts; ts=$(date -u +%Y-%m-%dT%H:%M:%SZ)
  gh issue comment "$issue" --body "Claimed by $worker at $ts (lease: ${lease_minutes}m)"
  gh issue edit "$issue" --add-label "worker:$worker:active"
}

release_claim() {
  local issue="$1" worker="$2" reason="${3:-completed}"
  gh issue comment "$issue" --body "Released by $worker at $(date -u +%Y-%m-%dT%H:%M:%SZ) — $reason"
  gh issue edit "$issue" --remove-label "worker:$worker:active"
}
```

### 3. Stale Work Recovery

A worker that dies mid-task leaves a claim behind. Reclaim it once the lease expires:

```bash
# Any claim older than the lease is fair game; drop the stale label
# and note on the issue that it's available again.
gh issue list --label "worker:$dead_worker:active" --state open --json number \
  --jq '.[].number' | while read -r n; do
    gh issue edit "$n" --remove-label "worker:$dead_worker:active"
    gh issue comment "$n" --body "Lease expired, available for reclaim"
  done
```

### 4. Heartbeat

For long-running work, refresh the claim before the lease expires by editing your claim comment with a new timestamp — otherwise another worker will legitimately steal the task mid-flight.

## Key Design Principles

1. **Comments as immutable logs** — GitHub preserves creation timestamps, giving natural ordering
2. **Labels for visibility** — a human can see worker activity at a glance
3. **Lease-based claiming** — prevents indefinite starvation when a worker dies
4. **UTC timestamps** — avoids clock-skew bugs across machines
5. **Idempotent operations** — re-claiming your own work is safe
6. **Graceful degradation** — API failures delay coordination, they don't corrupt it

## Limitations & Tradeoffs

| Concern | Reality | Mitigation |
|---|---|---|
| Rate limits | 5,000 req/hour authenticated | Cache claim state locally; sync at round boundaries |
| Latency | 1–3s roundtrip, eventually consistent | Use leases >5 min |
| Race conditions | Two workers can both briefly succeed | Read back after claiming; latest comment wins |
| Clock skew | Lease math differs per machine | UTC everywhere, ±2 min tolerance |

## Observability

Track: claims per worker per hour (imbalance), stale recoveries (failing workers), claim conflicts (race frequency), and rate-limit consumption. The issue comments are already a complete audit trail.

## Related Patterns

- **Leader election** — apply the same protocol to a single well-known issue
- **Job queue** — issues as jobs, labels as queue metadata
- **Failover** — primary/secondary worker coordination

## References

- [GitHub REST: Issues](https://docs.github.com/en/rest/issues), [Comments](https://docs.github.com/en/rest/issues/comments)
- [Martin Kleppmann — How to do distributed locking](https://martin.kleppmann.com/2016/02/08/how-to-do-distributed-locking.html)
