#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path


MEMORY_ROOT = Path(".agents/memory")
SCRIPT_DIR = Path(__file__).resolve().parent
PROMPT_TEMPLATE_PATH = SCRIPT_DIR.parent / "references" / "curator-prompt.md"

INDEX_TEMPLATE = """# Memory Index

Canonical durable memory for this workspace.
Keep this page compact, link-first, and easy to browse in Obsidian.

## User
_No user notes yet._

## Project
_No project notes yet._

## Feedback
_No feedback notes yet._

## Reference
_No reference notes yet._
"""

LOG_TEMPLATE = """# Memory Curator Log

Append-only operational log for wrapper-based memory curation.
"""

TOPIC_TEMPLATE = """---
title: General
description: Durable project facts captured from chat.
type: project
tags: [memory, project]
---

# General

## Summary

General durable project facts captured from chat.

## Facts

No curated memory yet.
"""

INDEX_PLACEHOLDERS = {
    "User": "_No user notes yet._",
    "Project": "_No project notes yet._",
    "Feedback": "_No feedback notes yet._",
    "Reference": "_No reference notes yet._",
}


@dataclass
class Paths:
    cwd: Path
    memory_dir: Path
    sources_dir: Path
    index_path: Path
    log_path: Path
    general_path: Path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Curate durable agent memory into .agents/memory using a separate Codex or Claude subprocess."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Create .agents/memory scaffold in the current working directory.")
    init_parser.set_defaults(handler=handle_init)

    capture_parser = subparsers.add_parser(
        "capture",
        help="Store a chat transcript in .agents/memory/sources and run a memory curator subprocess.",
    )
    capture_parser.add_argument("--backend", choices=("auto", "codex", "claude", "stub"), default="auto")
    capture_parser.add_argument("--input-file", type=Path, help="Read the chat transcript from a file instead of stdin.")
    capture_parser.add_argument("--source-name", default="current-chat", help="Short label used in the source transcript filename.")
    capture_parser.add_argument("--model", help="Optional model override forwarded to the selected backend.")
    capture_parser.add_argument(
        "--no-source-copy",
        action="store_true",
        help="Do not persist the provided transcript in .agents/memory/sources before curation.",
    )
    capture_parser.set_defaults(handler=handle_capture)
    return parser


def ensure_scaffold(cwd: Path) -> Paths:
    memory_dir = cwd / MEMORY_ROOT
    sources_dir = memory_dir / "sources"
    memory_dir.mkdir(parents=True, exist_ok=True)
    sources_dir.mkdir(parents=True, exist_ok=True)

    index_path = memory_dir / "MEMORY.md"
    log_path = memory_dir / ".log"
    general_path = memory_dir / "general.md"

    write_if_missing(index_path, INDEX_TEMPLATE)
    write_if_missing(log_path, LOG_TEMPLATE)
    write_if_missing(general_path, TOPIC_TEMPLATE)

    return Paths(
        cwd=cwd,
        memory_dir=memory_dir,
        sources_dir=sources_dir,
        index_path=index_path,
        log_path=log_path,
        general_path=general_path,
    )


def write_if_missing(path: Path, content: str) -> None:
    if not path.exists():
        path.write_text(content, encoding="utf-8")


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "chat"


def now_stamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%d-%H%M%SZ")


def load_transcript(input_file: Path | None) -> str:
    if input_file is not None:
        return input_file.read_text(encoding="utf-8").strip()

    if sys.stdin.isatty():
        raise SystemExit("No transcript provided. Pipe chat text on stdin or use --input-file.")

    return sys.stdin.read().strip()


def store_source(paths: Paths, transcript: str, source_name: str) -> Path:
    filename = f"{now_stamp()}-{slugify(source_name)}.md"
    source_path = paths.sources_dir / filename
    rendered = (
        "# Source Transcript\n\n"
        f"- **Captured**: {datetime.now(UTC).isoformat()}\n"
        f"- **Label**: {source_name}\n\n"
        "## Transcript\n\n"
        f"{transcript.rstrip()}\n"
    )
    source_path.write_text(rendered, encoding="utf-8")
    return source_path


def write_temp_source(paths: Paths, transcript: str, source_name: str) -> Path:
    temp_path = paths.memory_dir / f".tmp-{now_stamp()}-{slugify(source_name)}.md"
    temp_path.write_text(transcript.rstrip() + "\n", encoding="utf-8")
    return temp_path


def render_prompt(paths: Paths, source_path: Path) -> str:
    template = PROMPT_TEMPLATE_PATH.read_text(encoding="utf-8")
    return template.format(source_path=source_path, memory_dir=paths.memory_dir)


def choose_backend(requested: str) -> str:
    if requested != "auto":
        return requested

    codex_path = shutil.which("codex")
    claude_path = shutil.which("claude")
    env_backend = os.environ.get("AGENT_MEMORY_BACKEND")
    if env_backend in {"codex", "claude", "stub"}:
        return env_backend

    if os.environ.get("CLAUDECODE") or os.environ.get("CLAUDE_CODE_SIMPLE"):
        if claude_path:
            return "claude"

    if os.environ.get("CODEX_HOME"):
        if codex_path:
            return "codex"

    if codex_path:
        return "codex"
    if claude_path:
        return "claude"
    return "stub"


def handle_init(args: argparse.Namespace) -> int:
    paths = ensure_scaffold(Path.cwd())
    print(f"initialized: {paths.memory_dir}")
    return 0


def handle_capture(args: argparse.Namespace) -> int:
    transcript = load_transcript(args.input_file)
    if not transcript:
        raise SystemExit("Transcript is empty.")

    paths = ensure_scaffold(Path.cwd())
    source_path = None if args.no_source_copy else store_source(paths, transcript, args.source_name)
    source_for_prompt = source_path or write_temp_source(paths, transcript, args.source_name)
    backend = choose_backend(args.backend)

    try:
        if backend == "stub":
            summary = run_stub_backend(paths, source_for_prompt, transcript, args.source_name)
            print(summary)
            return 0

        prompt = render_prompt(paths, source_for_prompt)
        result = run_backend(backend=backend, cwd=paths.cwd, prompt=prompt, model=args.model)
        if result.returncode != 0:
            sys.stderr.write(result.stderr)
            return result.returncode

        sys.stdout.write(result.stdout)
        if result.stderr:
            sys.stderr.write(result.stderr)
        return 0
    finally:
        if source_path is None and source_for_prompt.exists():
            source_for_prompt.unlink(missing_ok=True)


def run_backend(*, backend: str, cwd: Path, prompt: str, model: str | None) -> subprocess.CompletedProcess[str]:
    if backend == "codex":
        cmd = [
            "codex",
            "exec",
            "--skip-git-repo-check",
            "-C",
            str(cwd),
            "--sandbox",
            "workspace-write",
            "-",
        ]
        if model:
            cmd[2:2] = ["-m", model]
        return subprocess.run(cmd, input=prompt, text=True, capture_output=True, cwd=cwd)

    if backend == "claude":
        cmd = [
            "claude",
            "-p",
            "--bare",
            "--permission-mode",
            "dontAsk",
        ]
        if model:
            cmd.extend(["--model", model])
        cmd.append(prompt)
        return subprocess.run(cmd, text=True, capture_output=True, cwd=cwd)

    raise ValueError(f"Unsupported backend: {backend}")


def run_stub_backend(paths: Paths, source_path: Path, transcript: str, source_name: str) -> str:
    insights = extract_stub_insights(transcript)
    if insights:
        write_general_memory(paths, insights)
        append_log(
            paths.log_path,
            f"- {datetime.now(UTC).isoformat()}: updated from `{source_path.name}` with {len(insights)} stub insight(s).",
        )
        return f"updated: stub wrote {len(insights)} insight(s) from {source_name}"

    append_log(
        paths.log_path,
        f"- {datetime.now(UTC).isoformat()}: no-update from `{source_path.name}`; no `INSIGHT:` markers found.",
    )
    return "no-update: stub found no INSIGHT markers"


def extract_stub_insights(transcript: str) -> list[str]:
    insights: list[str] = []
    for line in transcript.splitlines():
        if line.strip().lower().startswith("insight:"):
            candidate = line.split(":", 1)[1].strip()
            if candidate:
                insights.append(candidate)
    return insights


def write_general_memory(paths: Paths, insights: list[str]) -> None:
    body = paths.general_path.read_text(encoding="utf-8")
    if "No curated memory yet." in body:
        body = body.replace("No curated memory yet.", "")

    additions = []
    for insight in insights:
        bullet = f"- {insight}"
        if bullet not in body and bullet not in additions:
            additions.append(bullet)

    if additions:
        updated = body.rstrip() + "\n\n" + "\n".join(additions) + "\n"
        paths.general_path.write_text(updated, encoding="utf-8")

    ensure_index_entry(
        paths.index_path,
        section="Project",
        title="General",
        filename="general.md",
        hook="Durable project facts captured from chat.",
    )


def ensure_index_entry(
    index_path: Path,
    *,
    section: str,
    title: str,
    filename: str,
    hook: str,
) -> None:
    entry = f"- [{title}]({filename}) — {hook}"
    text = index_path.read_text(encoding="utf-8")
    if entry in text:
        return

    heading = f"## {section}"
    start = text.find(heading)
    if start == -1:
        if not text.endswith("\n"):
            text += "\n"
        text += f"\n{heading}\n{entry}\n"
        index_path.write_text(text, encoding="utf-8")
        return

    next_start = text.find("\n## ", start + len(heading))
    if next_start == -1:
        next_start = len(text)

    before = text[:start]
    current = text[start:next_start]
    after = text[next_start:]

    placeholder = INDEX_PLACEHOLDERS.get(section)
    if placeholder and placeholder in current:
        current = current.replace(placeholder, entry)
    else:
        current = current.rstrip() + "\n" + entry + "\n"

    index_path.write_text(before + current + after, encoding="utf-8")


def append_log(log_path: Path, entry: str) -> None:
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write("\n" + entry + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
