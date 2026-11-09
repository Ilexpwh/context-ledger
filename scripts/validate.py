#!/usr/bin/env python3
"""Validate package wiring and execute bundled hook commands in an isolated project."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/context-ledger/scripts"))
import ledger


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def validate():
    portable = json.loads((ROOT / "plugin.json").read_text())
    codex = json.loads((ROOT / ".codex-plugin/plugin.json").read_text())
    claude = json.loads((ROOT / ".claude-plugin/plugin.json").read_text())
    for manifest in (portable, codex, claude):
        require(manifest["name"] == "context-ledger", "Plugin identity mismatch")
        require(manifest["version"] == ledger.VERSION, "Version mismatch")
    for path in ROOT.rglob("*.json"):
        if ".git" not in path.parts and ledger.STORE not in path.parts:
            json.loads(path.read_text())
    skills = sorted((ROOT / "skills").glob("*/SKILL.md"))
    require(len(skills) == 4, "Expected four skills")
    for skill in skills:
        text = skill.read_text()
        require(text.startswith("---\n"), f"Missing skill frontmatter: {skill}")
        require(f"name: {skill.parent.name}\n" in text, f"Skill identity mismatch: {skill}")
        require("description: " in text.split("---", 2)[1], f"Missing description: {skill}")
        require((skill.parent / "agents/openai.yaml").is_file(), f"Missing Codex UI metadata: {skill}")
    require(len(list((ROOT / "commands").glob("*.md"))) == 8, "Expected eight command aliases")
    require("hooks" not in claude, "Claude auto-discovers hooks/hooks.json; avoid duplicate registration")
    require(codex["hooks"] == "./hooks/codex.json", "Codex must use its own protocol adapter")

    with tempfile.TemporaryDirectory(prefix="context ledger validation ") as folder:
        project = Path(folder)
        goal = (ROOT / "skills/context-ledger/assets/goal.example.md").read_text()
        state = (ROOT / "skills/context-ledger/assets/state.example.md").read_text()
        ledger.initialize(project, "fixture", goal)
        ledger.checkpoint(project, "fixture", state, 0)
        for host, filename in (("claude", "hooks.json"), ("codex", "codex.json")):
            ledger.bind(project, "fixture", host, host + "-fixture")
            hooks = json.loads((ROOT / "hooks" / filename).read_text())["hooks"]
            for event, groups in hooks.items():
                require(len(groups) == 1 and len(groups[0]["hooks"]) == 1, "Duplicate hook wiring")
                handler = groups[0]["hooks"][0]
                payload = {"hook_event_name": event, "session_id": host + "-fixture",
                           "cwd": str(project), "trigger": "manual", "source": "compact",
                           "stop_hook_active": False}
                env = dict(os.environ, PLUGIN_ROOT=str(ROOT), CLAUDE_PLUGIN_ROOT=str(ROOT))
                result = subprocess.run(handler["command"], shell=True, executable="/bin/sh", cwd=project,
                                        input=json.dumps(payload), text=True, capture_output=True,
                                        timeout=handler["timeout"], env=env)
                require(result.returncode == 0, f"{host}/{event}: {result.stderr}")
                if event in ("SessionStart", "UserPromptSubmit", "PostToolUse", "Stop") and result.stdout.strip():
                    value = json.loads(result.stdout)
                    require(isinstance(value, dict), "Hook output must be a JSON object")
                if host == "codex" and event == "PreCompact":
                    require(not result.stdout, "Codex PreCompact must be silent")
                if host == "claude" and event == "PreCompact":
                    require(0 < len(result.stdout) < 10000, "Claude compaction guidance must be bounded")
            handoff = project / ledger.STORE / "tasks/fixture/HANDOFF.md"
            require(handoff.is_file(), "Configured hook did not create the recovery handoff")
    print("Validated: four skills, eight commands, three manifests, two host adapters, twelve hook executions.")


if __name__ == "__main__":
    validate()
