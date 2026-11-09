#!/usr/bin/env python3
"""Install a project-local skill bundle and optional hooks, preserving other config."""
import argparse
import hashlib
import json
from pathlib import Path
import shlex
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/context-ledger/scripts"))
from ledger import LedgerError, atomic_write, bounded_read, safe_path, write_json


def sha(data):
    return hashlib.sha256(data).hexdigest()


def install(project, host, hooks=False, uninstall=False):
    project = Path(project).resolve()
    if not project.is_dir():
        raise LedgerError("Project must be an existing directory")
    config_dir = ".codex" if host == "codex" else ".claude"
    receipt_path = safe_path(project, config_dir, "context-ledger-install.json")
    receipt = json.loads(bounded_read(receipt_path)) if receipt_path.exists() else {"files": {}, "groups": {}}
    target_root = ".agents/skills" if host == "codex" else ".claude/skills"
    hook_path = safe_path(project, config_dir, "hooks.json" if host == "codex" else "settings.local.json")
    config = json.loads(bounded_read(hook_path)) if hook_path.exists() else {}
    if not isinstance(config, dict) or not isinstance(config.get("hooks", {}), dict):
        raise LedgerError("Existing hook configuration is not an object; leave it untouched")
    planned = {}
    if not uninstall:
        for source in sorted((ROOT / "skills").rglob("*")):
            if source.is_file() and "__pycache__" not in source.parts and source.suffix != ".pyc":
                relative = str(Path(target_root) / source.relative_to(ROOT / "skills"))
                planned[relative] = source.read_bytes()
    # Preflight every collision before any writes; upgrades only replace unchanged owned files.
    for relative in set(receipt["files"]) | set(planned):
        target = safe_path(project, relative)
        if target.exists():
            actual = sha(target.read_bytes())
            expected = receipt["files"].get(relative)
            if expected is not None and actual != expected:
                raise LedgerError(f"Installed file was modified; preserve or move it before updating: {relative}")
            if expected is None:
                raise LedgerError(f"Unowned file collision: {relative}")
    hooks_map = config.get("hooks", {})
    installed_cli = str(safe_path(project, target_root, "context-ledger/scripts/ledger.py"))
    for event, existing in hooks_map.items():
        if not isinstance(existing, list):
            raise LedgerError(f"Malformed hooks for {event}")
        owned = receipt.get("groups", {}).get(event, [])
        for group in existing:
            if group not in owned and isinstance(group, dict):
                for handler in group.get("hooks", []):
                    command = handler.get("command", "") if isinstance(handler, dict) else ""
                    try:
                        tokens = shlex.split(command)
                    except ValueError:
                        tokens = []
                    if installed_cli in tokens or installed_cli in command:
                        raise LedgerError("A hook referencing this installation was customized; reconcile it before upgrading or uninstalling")
    for event, groups in receipt.get("groups", {}).items():
        existing = hooks_map.get(event, [])
        if not isinstance(existing, list):
            raise LedgerError(f"Malformed hooks for {event}")
        hooks_map[event] = [group for group in existing if group not in groups]
        if not hooks_map[event]:
            hooks_map.pop(event)
    groups = {}
    if not uninstall and (hooks or receipt.get("groups")):
        cli = Path(installed_cli)
        command = "python3 -I " + shlex.quote(str(cli)) + " --host " + host + " hook"
        for event in ("SessionStart", "UserPromptSubmit", "PostToolUse", "PreCompact", "Stop", "SessionEnd"):
            if not isinstance(hooks_map.get(event, []), list):
                raise LedgerError(f"Malformed hooks for {event}")
            group = {"hooks": [{"type": "command", "command": command, "timeout": 15}]}
            hooks_map.setdefault(event, []).append(group)
            groups[event] = [group]
    for relative, data in planned.items():
        atomic_write(safe_path(project, relative), data.decode("utf-8"))
    for relative in set(receipt["files"]) - set(planned):
        safe_path(project, relative).unlink(missing_ok=True)
    if hooks or receipt.get("groups"):
        if hooks_map:
            config["hooks"] = hooks_map
        else:
            config.pop("hooks", None)
        write_json(hook_path, config)
    if uninstall:
        receipt_path.unlink(missing_ok=True)
    else:
        write_json(receipt_path, {"schema": 1, "files": {k: sha(v) for k, v in planned.items()}, "groups": groups})
    return {"host": host, "project": str(project), "skills_files": len(planned),
            "hooks_installed": bool(groups), "uninstalled": uninstall,
            "next": "Restart the host. For Codex, review/trust the hook definitions in /hooks. Do not also install the native plugin in this project."}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True)
    parser.add_argument("--host", choices=("codex", "claude"), required=True)
    parser.add_argument("--hooks", action="store_true")
    parser.add_argument("--uninstall", action="store_true")
    args = parser.parse_args()
    try:
        print(json.dumps(install(args.project, args.host, args.hooks, args.uninstall), indent=2))
    except (OSError, ValueError, LedgerError) as exc:
        print(f"context-ledger install: {exc}", file=sys.stderr)
        raise SystemExit(1)
