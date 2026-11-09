import importlib.util
import json
from pathlib import Path
import tempfile
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("installer", ROOT / "scripts/install.py")
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class InstallTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="install space ' quote ")
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_both_hosts_merge_idempotently_and_uninstall_owned_files(self):
        for host, directory, name in (("codex", ".codex", "hooks.json"), ("claude", ".claude", "settings.local.json")):
            config = self.root / directory / name
            config.parent.mkdir(exist_ok=True)
            existing = {"hooks": {"Stop": [{"hooks": [{"type": "command", "command": "echo existing"}]}]}, "unrelated": True}
            config.write_text(json.dumps(existing))
            installer.install(self.root, host, hooks=True)
            first = json.loads(config.read_text())
            installer.install(self.root, host, hooks=True)
            self.assertEqual(json.loads(config.read_text()), first)
            self.assertEqual(len(first["hooks"]["Stop"]), 2)
            self.assertTrue(first["unrelated"])
            installer.install(self.root, host, uninstall=True)
            self.assertEqual(json.loads(config.read_text()), existing)

    def test_user_edits_block_upgrade_before_any_writes(self):
        installer.install(self.root, "codex")
        target = self.root / ".agents/skills/context-ledger/SKILL.md"
        target.write_text("user-customized")
        with self.assertRaises(installer.LedgerError):
            installer.install(self.root, "codex", hooks=True)
        self.assertEqual(target.read_text(), "user-customized")
        self.assertFalse((self.root / ".codex/hooks.json").exists())

    def test_unowned_collision_is_not_overwritten(self):
        target = self.root / ".agents/skills/context-ledger/SKILL.md"
        target.parent.mkdir(parents=True)
        target.write_text("existing independent skill")
        with self.assertRaises(installer.LedgerError):
            installer.install(self.root, "codex")
        self.assertEqual(target.read_text(), "existing independent skill")

    def test_symlink_install_directory_is_refused(self):
        with tempfile.TemporaryDirectory() as outside:
            (self.root / ".claude").symlink_to(outside, target_is_directory=True)
            with self.assertRaises(installer.LedgerError):
                installer.install(self.root, "claude", hooks=True)
            self.assertEqual(list(Path(outside).iterdir()), [])

    def test_installed_hook_executes_with_spaces_and_quotes_in_path(self):
        installer.install(self.root, "claude", hooks=True)
        from ledger import initialize
        goal = (ROOT / "skills/context-ledger/assets/goal.example.md").read_text()
        initialize(self.root, "checkout", goal, "claude", "test-session")
        config = json.loads((self.root / ".claude/settings.local.json").read_text())
        command = config["hooks"]["SessionStart"][0]["hooks"][0]["command"]
        result = subprocess.run(command, shell=True, executable="/bin/sh", capture_output=True, text=True,
                                input=json.dumps({"cwd": str(self.root), "hook_event_name": "SessionStart", "session_id": "test-session"}),
                                timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("exactly one order", json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"])

    def test_modified_hook_is_not_orphaned_on_uninstall(self):
        installer.install(self.root, "codex", hooks=True)
        path = self.root / ".codex/hooks.json"
        config = json.loads(path.read_text())
        config["hooks"]["Stop"][0]["hooks"][0]["timeout"] = 30
        path.write_text(json.dumps(config))
        with self.assertRaises(installer.LedgerError):
            installer.install(self.root, "codex", uninstall=True)
        self.assertTrue((self.root / ".agents/skills/context-ledger/scripts/ledger.py").exists())


if __name__ == "__main__":
    unittest.main()
