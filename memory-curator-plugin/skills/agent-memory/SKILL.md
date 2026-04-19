---
name: agent-memory
description: Save durable, non-obvious project memory by running the memory curator as a separate process. Use when the current chat produced insights, constraints, decisions, preferences, or external references that are not obvious from the repository. Writes to .agents/memory in the directory where the command is launched.
---

# agent-memory

Use this wrapped skill when a conversation produced durable knowledge that should survive the session.

## When To Use

Run the wrapper after a task reaches a stable conclusion and the chat revealed at least one of:

- an undocumented constraint or workflow
- design rationale not already written down
- a user or team preference that should affect future work
- an external reference or project fact not derivable from the repo
- a gotcha discovered during debugging or implementation

Do not run it for transient status, generic advice, code structure, file paths, or edits already obvious from code, docs, tests, `git diff`, `AGENTS.md`, or `CLAUDE.md`.

## Command

Run from the target repository root, or anywhere inside the workspace whose memory you want to update:

```bash
<plugin-root>/scripts/agent-memory capture --backend auto
```

When resolving paths from this skill directory, the wrapper lives at:

```bash
../../scripts/agent-memory
```

The wrapper chooses `codex` or `claude` automatically unless you force `--backend codex` or `--backend claude`.

## Input

Pipe the relevant transcript or a compact summary into the command. Prefer concise summaries that preserve the actual durable insight.

## Output

Memory is always stored relative to the launch directory:

- `.agents/memory/MEMORY.md`
- `.agents/memory/.log`
- `.agents/memory/*.md`
- `.agents/memory/sources/`

`MEMORY.md` is the canonical, Obsidian-friendly index. Topic notes should stay structured and linkable, not free-form dumps.

## Notes

- The curation step runs in a separate subprocess via `codex exec` or `claude -p`.
- The subprocess should only edit `.agents/memory/`.
- The wrapper keeps the source chat under `sources/` for provenance unless `--no-source-copy` is used.
