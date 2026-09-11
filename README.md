# Squad template

A Claude Code starting point. Create a repo from this template and the squad is available in it immediately — no install step, because agents are project-scoped and `.claude/` is what carries them.

## What you get

**7 agents** — dispatch with the `Agent` tool, or ask for them by name.

| Agent | Use it when | Edits code |
|---|---|---|
| `architect` | The approach isn't obvious — multi-file work, migrations, refactors. Returns a plan | No |
| `builder` | The approach is settled and the work is mechanical | Yes |
| `tester` | You want a change independently confirmed, with real command output | No |
| `reviewer` | You want a second opinion on a diff from someone who didn't write it | No |
| `coach` | Work hasn't started or the task feels too big. Returns a decomposition | No |
| `visualizer` | The structure is easier to see than to read. Writes an HTML/SVG diagram | Writes the diagram |
| `explainer` | You want to understand existing code rather than change it | No |

Build flow: `architect → builder → tester → reviewer`. The other three are standalone and shouldn't be wired into it. Don't run the chain for a two-line fix — the overhead exceeds the benefit.

**8 skills** — `spawn-squad`, `reflect`, `fact-checking`, `secrets-management`, `gh-auth-isolation`, `github-distributed-coordination`, `incident-response`, `chrome-devtools-mcp`.

## Checking the definitions

```
python3 scripts/validate-squad.py
```

Checks all 15 definitions: frontmatter parses, required keys present and non-empty, each `name` matching its filename or directory. Exit 0 pass, 1 failure, 2 cannot run (needs `pyyaml`).

Worth running after editing an agent or skill: **a malformed definition fails to load silently, with no error.** That is the failure this exists to catch. Eight of these skills were adapted from an upstream repo and four arrived with no frontmatter at all.

## Things worth knowing

- **Subagents run headless.** They return one report and cannot ask a question mid-run. Anything needing back-and-forth belongs in the main conversation.
- **`Skill` in an agent's `tools` list is load-bearing.** It is the only thing letting `visualizer` and `explainer` load skills; removing it quietly reduces them to plain readers.
- **Agent registration lags by a turn.** A newly added agent usually appears on the next turn, not immediately — a missing agent right after a file change isn't necessarily a broken definition.
- **`diagram-design` and `adhd-learning-coach` are deliberately absent.** Both sync from the Claude account and already load in every session, so a copy here would add bulk and a second place to drift. `visualizer` still draws diagrams.
- **Three skills carry environment notes.** Claude Code on the web has no `gh` CLI and no credential-store CLI, so `gh-auth-isolation` doesn't apply there, `github-distributed-coordination` needs its `gh` → MCP translation table, and `secrets-management` reduces to its environment-variable tier.

## Why a template rather than a plugin

`/plugin` does not exist in Claude Code on the web — it returns `/plugin isn't available in this environment`. Subagents have no account-sync path either, unlike skills. So on the web, `.claude/` in the repo is the only mechanism that reaches them, and a template is the way to get it there without copying by hand each time.

Skills *do* sync from the Claude account, so uploading these eight there makes them available everywhere without any repo at all — worth doing separately.

## Upstream

Eight skills are adapted from [tamirdresher/squad-skills](https://github.com/tamirdresher/squad-skills) (MIT), rewritten from GitHub Copilot CLI / "Squad" conventions to Claude Code's.
