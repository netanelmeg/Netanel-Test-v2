---
name: secrets-management
description: Pattern for keeping secrets out of git while still making them available to Claude Code at runtime. Use whenever a task involves API keys, tokens, passwords, or .env files.
---

# Secrets Management

> **Rule Zero:** No secret value is ever committed to git. Period.

> **In Claude Code on the web, tiers 1–2 below are unavailable.** That environment has no OS credential store and no vault CLI (verified: `secret-tool`, `security`, `cmdkey`, and `pass` are all absent). Secrets there come from **environment variables configured on the environment itself** — tier 4 — which is the only tier that works. Tiers 1–3 apply to local machines.

## Where Secrets Live (Priority Order)

| Priority | Source | Example | Notes |
|----------|--------|---------|-------|
| 1 | **OS credential store** | macOS Keychain, Windows Credential Manager, `secret-tool` on Linux | Most secure; survives reboots, not visible in shell history |
| 2 | **Secret manager / vault** | 1Password CLI, Bitwarden CLI, cloud secret manager | Good when secrets are shared across machines or teammates |
| 3 | **Machine-local `.env`** (gitignored) | `~/.config/<project>/.env` | Fallback when no credential store is available |
| 4 | **Environment variable** | `$API_KEY` | Already set in the session (e.g. by CI) |

## How to Add a New Secret

1. **Add to `.env.example`** — document the variable name, description, and where to get it. No values.
2. **Add a setup script entry** (e.g. `scripts/setup-secrets.sh`) recording:
   - the env var name
   - the credential-store key (or none, if it's env-only)
   - whether it's required
3. **Store the actual value** locally, e.g.:
   ```bash
   # macOS
   security add-generic-password -a "$USER" -s my-new-secret -w "actual-value"
   # Linux (libsecret)
   secret-tool store --label="my-new-secret" service my-new-secret
   ```
4. **Document it** in the repo so the next person (or agent) knows it exists and how to populate it.

## Cross-Machine Sync

**Secrets do NOT sync between machines automatically.** Each environment (laptop, cloud sandbox, CI runner) sets up its own secrets independently — never by copying a `.env` file through git or chat.

## `.env.example` Pattern

`.env.example` in the repo root lists every required environment variable with a description but **no values**. It's documentation and a template, and it's the only variant of the file that should ever be committed.

## `.gitignore` Protection

Make sure `.gitignore` includes:
- `*.env`, `.env.*` — environment files
- `*secret*`, `*credential*` — anything named with sensitive terms
- `*.key`, `*.pem` — cryptographic material
- `!.env.example` — the template is explicitly allowed

## Rotation Procedures

When a secret is compromised or needs rotation:
1. Generate a new value from the provider
2. Update it everywhere it's stored (credential store, vault, CI secrets)
3. Revoke the old value at the provider
4. Document that rotation occurred
5. If the secret was ever committed to git history, treat it as permanently compromised — rotate regardless of whether the commit was reverted

## Security Checklist

- [ ] No secret values in any committed file
- [ ] `.env.example` has descriptions only, no values
- [ ] `.gitignore` blocks `*.env`, `*secret*`, `*credential*`, `*.key`, `*.pem`
- [ ] A setup/validation script checks all required secrets are present before running
- [ ] Screenshots or logs with visible secrets are removed before committing
