---
name: gh-auth-isolation
description: Stop concurrent agent sessions from fighting over the GitHub CLI's global auth state when working across repos owned by different accounts (personal vs work/enterprise). Use when `gh` returns the wrong account intermittently or fails only when several sessions run at once.
---

# GitHub Auth Isolation

> **Does not apply in Claude Code on the web.** That environment has **no `gh` CLI** (verified: `command -v gh` returns nothing) — GitHub access goes through the `mcp__github__*` MCP tools, which carry their own per-session credentials and share no global state. The failure mode below cannot occur there, so this skill is only relevant on a local machine with `gh` installed.

## Problem

When several agent sessions or scripts run across repos belonging to different GitHub accounts, they fight over the CLI's **global** auth state. Each one switches to the account it needs, breaking the others on their next command.

Symptoms:
- Intermittent failures across repos that disappear when only one session runs
- `gh api user` returns the wrong account
- Failures are timing-dependent, not reproducible in isolation

## Root Cause

`gh auth switch --user X` mutates **global** state in the `gh` keyring. Every process on the machine shares it. Process A switches to account X, process B switches to account Y, and A's next API call silently uses Y.

## Solution: Per-Process `GH_TOKEN`

Don't switch global auth. Extract the token for the account you need and set it as a **process-local** environment variable:

```bash
# Pick the account from the repo's remote
remote_url=$(git remote get-url origin)
if [[ "$remote_url" == *"your-work-org"* ]]; then
  account="your-work-account"
else
  account="your-personal-account"
fi

# Read the token WITHOUT switching global state
export GH_TOKEN="$(gh auth token --user "$account")"

# Every gh command in THIS process now uses the right account.
# Other processes are unaffected.
```

Wrap it so a missing token falls back instead of running as the wrong user:

```bash
token=$(gh auth token --user "$account" 2>/dev/null || true)
if [[ -n "$token" ]]; then
  export GH_TOKEN="$token"
else
  echo "WARN: no stored token for $account — not switching global auth" >&2
  exit 1
fi
```

## When to Use

- Multiple agent sessions or watch loops running against repos on different accounts
- CI/CD environments where several `gh`-authenticated processes run concurrently
- Any machine where personal and work repos coexist

## Key Insight

This is a classic concurrency bug: shared mutable state (global auth) accessed by parallel processes. The fix is the standard one — eliminate the sharing by making the state process-local.
