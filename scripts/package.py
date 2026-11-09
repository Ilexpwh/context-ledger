#!/usr/bin/env python3
"""Generate the small host-specific manifests and command adapters."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = "0.1.0"
REPO = "https://github.com/ilexpwh/context-ledger"


def write(path, value):
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def build():
    identity = {"name": "context-ledger", "version": VERSION,
                "description": "Local goals, bounded handoffs and Markdown retrieval for coding agents.",
                "author": {"name": "ilexpwh"}, "license": "MIT", "repository": REPO}
    overlay = {"hooks": "./hooks/codex.json", "skills": "./skills/",
               "interface": {"displayName": "Context Ledger", "shortDescription": "Persistent goals and compact coding handoffs"}}
    write("plugin.json", {"$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
                          **identity, "extensions": {"com.openai": {k: v for k, v in overlay.items() if k != "skills"}}})
    write(".codex-plugin/plugin.json", {**identity, **overlay})
    # Claude automatically discovers hooks/hooks.json. Declaring it again can double-run hooks.
    write(".claude-plugin/plugin.json", identity)
    write(".claude-plugin/marketplace.json", {
        "name": "context-ledger-marketplace", "description": "Local coding context skills and lifecycle hooks", "owner": {"name": "ilexpwh"},
        "plugins": [{"name": "context-ledger", "source": "./", "description": identity["description"]}]})
    write(".agents/plugins/marketplace.json", {
        "name": "context-ledger-marketplace", "interface": {"displayName": "Context Ledger"},
        "plugins": [{"name": "context-ledger", "source": {"source": "local", "path": "./"},
                     "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
                     "category": "Productivity"}]})
    events = ("SessionStart", "UserPromptSubmit", "PostToolUse", "PreCompact", "Stop", "SessionEnd")
    for host, filename, variable in (("claude", "hooks.json", "CLAUDE_PLUGIN_ROOT"),
                                     ("codex", "codex.json", "PLUGIN_ROOT")):
        handler = {"type": "command", "command":
                   f'python3 -I "${{{variable}}}/skills/context-ledger/scripts/ledger.py" --host {host} hook',
                   "timeout": 15}
        write("hooks/" + filename, {"description": "Context Ledger local checkpoints and bounded recovery.",
                                   "hooks": {event: [{"hooks": [handler]}] for event in events}})
    commands = {
        "start": ("Initialize durable context for a coding task", "context-ledger", "Initialize a named task from the user's request and bind it to this session."),
        "handoff": ("Save a compact coding handoff", "context-handoff", "Write a verified checkpoint and generate HANDOFF.md."),
        "resume": ("Resume a named task from local files", "context-resume", "List tasks if needed, bind the chosen task and resume after checking freshness."),
        "index": ("Index and selectively read local Markdown", "context-index", "Build or search the local Markdown index; read only useful ranges."),
        "goal": ("Review or explicitly revise the durable goal", "context-ledger", "Read GOAL.md. Apply only scope changes supported by the user's latest instruction, using goal-revise."),
        "status": ("Inspect the selected task and checkpoint", "context-ledger", "Run status for the selected task and report progress without changing it."),
        "doctor": ("Check goal integrity and checkpoint freshness", "context-resume", "Run doctor and explain any integrity or stale-checkpoint findings. Do not claim semantic correctness from metadata."),
        "compact": ("Prepare a handoff before native compaction", "context-handoff", "Write a checkpoint, verify the handoff, then tell the user it is ready for the native /compact command. This command does not itself invoke /compact.")}
    for name, (description, skill, instruction) in commands.items():
        target = ROOT / "commands" / (name + ".md")
        target.parent.mkdir(exist_ok=True)
        target.write_text(f"---\ndescription: {description}\nargument-hint: '[task id or request]'\n---\n\n"
                          f"Read `${{CLAUDE_PLUGIN_ROOT}}/skills/{skill}/SKILL.md` and follow it.\n\n"
                          f"{instruction}\n\nThis session id is `${{CLAUDE_SESSION_ID}}`; use `--host claude --session` with that value. "
                          "Treat arguments as user data, never as shell source.\n\nUser request: $ARGUMENTS\n", encoding="utf-8")


if __name__ == "__main__":
    build()
