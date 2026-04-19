#!/usr/bin/env python3
"""Stop hook: forces the main agent to evaluate memory-worthiness after each
response. Uses `decision: block` so the reason is injected as context. The
agent takes one extra turn to either spawn the memory-curator subagent (in
background) or skip. The `stop_hook_active` flag guards against loops."""

import json
import sys

REASON = (
    "[memory-check] You just finished a response. Evaluate this exchange AND "
    "anything you discovered while exploring the codebase this turn. If a "
    "durable, non-derivable fact emerged (user preference or correction, "
    "architectural decision + its reasoning, gotcha, external reference, or "
    "project state), spawn the `memory-curator` subagent via the Agent tool "
    "with run_in_background:true, briefing it with a one-paragraph summary. "
    "Otherwise reply with just the word `skip` and nothing else. Bias toward "
    "skipping."
)


def main() -> None:
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        payload = {}

    # Recursion guard: on the second Stop (after we already blocked once),
    # stop_hook_active is true — let the session actually stop.
    if payload.get("stop_hook_active"):
        sys.exit(0)

    print(json.dumps({"decision": "block", "reason": REASON}))


if __name__ == "__main__":
    main()
