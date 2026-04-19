# Memory Curator Plugin

**A Claude Code plugin plus wrapped skill that keeps a compact, durable per-repo memory at `.agents/memory/`.**

After every response, a `Stop` hook asks the main agent "did anything memorable happen this turn?" If yes, it spawns a small background subagent that filters, deduplicates, and writes the fact to a kebab-case topic file under `.agents/memory/` and indexes it in `MEMORY.md`. If not, the agent skips.

Uses only your existing Claude Code auth for the Claude plugin path. The wrapped skill / CLI can also be used from Codex.

## Wrapped skill / CLI

This package also includes a wrapped skill and CLI entrypoint for manual use from either Codex or Claude Code:

```bash
/path/to/memory-curator-plugin/scripts/agent-memory capture --backend auto
```

Pipe in the relevant transcript or a compact summary. The wrapper:

- runs a separate `codex` or `claude` subprocess
- stores provenance in `.agents/memory/sources/`
- writes memory relative to the directory where you launch it

The skill lives at `skills/agent-memory/SKILL.md`.

## How it works

```
 ┌──────────────┐     Stop hook      ┌────────────────┐
 │ Main agent   │ ─────────────────► │ memory-check.py │
 │ finishes     │                    └────────┬────────┘
 │ a response   │                             │
 └──────┬───────┘           decision: block + reason
        │                             │
        │◄────────────────────────────┘
        │  (extra turn: evaluate memory-worthiness)
        │
        ▼
  spawn `memory-curator` subagent in background ──►  .agents/memory/
        │                                             ├── MEMORY.md (index)
        │                                             └── <topic>.md (fact)
        ▼
  or just reply `skip`
```

- **Stop hook** (`hooks/memory-check.py`): fires at end of every turn, returns `{"decision": "block", "reason": "..."}` so Claude Code injects a memory-evaluation prompt. Recursion guarded with `stop_hook_active`.
- **Subagent** (`agents/memory-curator.md`, model: `haiku`): applies a strict save filter (non-derivable, durable, specific), writes only under `.agents/memory/`, and keeps `MEMORY.md` as a compact grouped index with link-first entries.

Memory lives in the **consuming repo**, not in this plugin. Each repo you open in Claude Code gets its own `.agents/memory/`.

## What gets saved

- **user** — role, responsibilities, preferences, knowledge level.
- **feedback** — corrections AND validated approaches (with *why* + *how to apply*).
- **project** — ownership, deadlines, motivations behind active work.
- **reference** — pointers to Linear projects, Grafana dashboards, Slack channels, docs.

## What does NOT get saved

- Code patterns, file paths, architecture — re-read the code.
- What changed this session — `git log` / `git diff` have it.
- Fix recipes — the commit IS the fix.
- Ephemeral task state.

The subagent is biased toward skipping. Noisy memory is worse than missing memory.

## Install

### Via Claude Code plugin marketplace

```bash
/plugin marketplace add dumcps/memory-curator-plugin
/plugin install memory-curator@memory-curator-plugin
```

Restart Claude Code.

### Locally (development or this repo itself)

```bash
claude --plugin-dir ./memory-curator-plugin
```

### Global skill for Codex

Codex does not support the Claude `Stop` hook flow directly, so the Codex path is:

1. install the wrapped skill globally
2. wire root instructions so Codex reads and writes memory intentionally
3. add lightweight repo instructions so each consuming repository knows memory is available

Install the skill and wrapper into your Codex home:

```bash
mkdir -p ~/.codex/skills ~/.codex/scripts
cp -R ./memory-curator-plugin/skills/agent-memory ~/.codex/skills/agent-memory
cp ./memory-curator-plugin/scripts/agent-memory ~/.codex/scripts/agent-memory
chmod +x ~/.codex/scripts/agent-memory
```

Restart Codex after installing the files.

### Wire Codex root instructions

Add something like this to `~/.codex/AGENTS.md`:

```md
If `.agents/memory/MEMORY.md` exists in the current repository, treat it as the canonical durable repo memory index and consult it when relevant. Follow its links to topic notes when you need detail.

When a chat produces a durable, non-obvious fact that is not already obvious from code, docs, tests, git history, or existing memory, use the global `agent-memory` skill to persist it.
```

This gives Codex two behaviors:

- read repo memory when relevant
- save new durable memory deliberately

### Wire the consuming repository

Add repo-level guidance to that repo's `AGENTS.md`:

```md
If `.agents/memory/MEMORY.md` exists, treat it as durable repo memory and consult it when relevant.

When a chat produces a durable, non-obvious fact that is not already obvious from code, docs, tests, git history, or existing memory, update repo memory by running the memory curator wrapper as a separate process from the repo root:

`printf '%s\n' '<compact summary of the durable insight>' | ~/.codex/scripts/agent-memory capture --backend codex`
```

Initialize memory once from the consuming repo root:

```bash
~/.codex/scripts/agent-memory init
```

This creates:

- `.agents/memory/MEMORY.md`
- `.agents/memory/general.md`
- `.agents/memory/.log`
- `.agents/memory/sources/`

### Codex behavior note

The global skill does **not** make Codex fully automatic by itself.

Unlike Claude Code, Codex will not run a stop hook after every response just because the skill is installed. The skill becomes available globally, but Codex still needs explicit instruction via root / repo `AGENTS.md` to consult memory and use `agent-memory` when appropriate.

## Optional: surface memory in your CLAUDE.md

Add to the repo's `CLAUDE.md` so the index is always in context:

```
@.agents/memory/MEMORY.md
```

## Consume memory

`MEMORY.md` is the index. Each entry points at a topic file with this frontmatter:

```markdown
---
title: Short Name
description: one-line hook under 150 chars
type: user | feedback | project | reference
tags: [memory, <type>]
---

# Short Name

## Summary

<durable fact or rule>
```

`MEMORY.md` should remain a compact, grouped index with normal Markdown links:

```markdown
## User
- [Title](topic-file.md) — one-line hook

## Project
- [Title](topic-file.md) — one-line hook
```

For `feedback` and `project`, include:

- `## Why`
- `## How To Apply`

Add `## Links` when cross-references help future agents. Keep the notes readable in plain Markdown and Obsidian.

## Trade-offs

- Stop hooks with `decision: block` add **one extra evaluation turn** per response. Accepted trade-off: the alternative (`UserPromptSubmit`) misses insights that emerged from the agent's own codebase exploration.
- Memory is best-effort. The main agent can still mis-classify what's memorable; the subagent's filter is the second line of defense.
- `.agents/memory/.log` tracks curator decisions (saves + skips) for debugging. Gitignored.

## Files

```
memory-curator-plugin/
├── .claude-plugin/
│   └── plugin.json          # Manifest + Stop hook registration
├── agents/
│   └── memory-curator.md    # Background subagent (haiku)
├── hooks/
│   └── memory-check.py      # Stop hook: injects memory-evaluation prompt
├── scripts/
│   └── agent-memory         # Manual wrapper for Codex/Claude subprocess use
├── skills/
│   └── agent-memory/        # Wrapped skill + prompt + Python runner
└── README.md
```

## License

MIT
