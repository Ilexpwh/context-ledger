import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "skills/context-ledger/scripts/ledger.py"
sys.path.insert(0, str(CLI.parent))
import ledger

GOAL = """# Task
## Objective
Fix the checkout race without changing the API.
## Constraints
- Preserve the public API and unrelated edits.
## Acceptance criteria
- AC1: Concurrent submissions create one order.
- AC2: Existing checkout tests pass.
"""
STATE = """## Current state
Reproduced the race; src/checkout.py is unchanged.
## Decisions
Guard the pending request; retry after failure remains allowed.
## Verification
Baseline checkout tests passed. Regression test not yet written.
## Dead ends
Debounce permits duplicate requests after the timer.
## Next actions
Add the regression test, then implement the pending guard.
## Open questions
None.
"""


class LedgerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="ledger tests ")
        self.root = Path(self.tmp.name).resolve()
        self.git("init", "-q")
        self.git("config", "user.name", "Test")
        self.git("config", "user.email", "test@example.invalid")
        (self.root / "README.md").write_text("# Checkout\n\n## Contract\nOnly one order.\n")
        self.git("add", "README.md")
        self.git("commit", "-qm", "fixture")
        ledger.initialize(self.root, "checkout", GOAL, "claude", "chat-a")

    def tearDown(self):
        self.tmp.cleanup()

    def git(self, *args):
        return subprocess.run(["git", "-C", str(self.root), *args], capture_output=True, check=True)

    def cp(self, task="checkout", expected=0, text=STATE):
        return ledger.checkpoint(self.root, task, text, expected, "claude", "chat-a")

    def event(self, name, host="claude", session="chat-a", **extra):
        return ledger.hook(self.root, host, {"session_id": session, "hook_event_name": name, **extra})

    def run_cli(self, *args, stdin=None):
        return subprocess.run([sys.executable, "-I", str(CLI), "--root", str(self.root), *args],
                              input=stdin, text=True, capture_output=True)

    def test_initialization_does_not_overwrite(self):
        with self.assertRaises(ledger.LedgerError):
            ledger.initialize(self.root, "checkout", GOAL.replace("race", "bug"))
        self.assertEqual(ledger.load_goal(self.root, "checkout")[0], GOAL)

    def test_runtime_memory_is_git_ignored(self):
        self.assertEqual(self.git("status", "--porcelain").stdout, b"")

    def test_no_global_task_fallback(self):
        with self.assertRaises(ledger.LedgerError):
            ledger.resolve_task(self.root)
        hint = self.event("SessionStart", session="new-chat")
        text = hint["hookSpecificOutput"]["additionalContext"]
        self.assertIn("unbound", text)
        self.assertNotIn("checkout race", text)

    def test_sessions_and_hosts_are_isolated(self):
        ledger.initialize(self.root, "billing", GOAL.replace("checkout", "billing"), "codex", "chat-a")
        self.assertEqual(ledger.resolve_task(self.root, host="claude", session="chat-a"), "checkout")
        self.assertEqual(ledger.resolve_task(self.root, host="codex", session="chat-a"), "billing")

    def test_unbound_hint_is_not_repeated_on_every_prompt(self):
        self.assertIsNotNone(self.event("UserPromptSubmit", session="unbound"))
        self.assertIsNone(self.event("UserPromptSubmit", session="unbound"))
        self.assertIsNotNone(self.event("SessionStart", session="unbound", source="compact"))

    def test_nested_directory_discovers_project(self):
        child = self.root / "src" / "nested"
        child.mkdir(parents=True)
        self.assertEqual(ledger.project_root(child), self.root)

    def test_nested_repo_is_a_hard_boundary(self):
        child = self.root / "nested"
        child.mkdir()
        subprocess.run(["git", "-C", str(child), "init", "-q"], check=True)
        self.assertEqual(ledger.project_root(child), child)

    def test_checkpoint_revision_prevents_lost_updates(self):
        self.cp()
        with self.assertRaises(ledger.LedgerError):
            self.cp(expected=0, text=STATE.replace("unchanged", "changed"))
        self.assertEqual(ledger.load_state(self.root, "checkout")[1], STATE)

    def test_lock_contention_leaves_files_unchanged(self):
        with ledger.locked(self.root):
            with self.assertRaises(ledger.LedgerError):
                self.cp()
        self.assertEqual(ledger.load_state(self.root, "checkout")[0]["revision"], 0)

    def test_goal_drift_is_detected(self):
        path = ledger.task_dir(self.root, "checkout") / "GOAL.md"
        path.write_text(GOAL.replace("one order", "two orders"))
        with self.assertRaises(ledger.LedgerError):
            ledger.load_goal(self.root, "checkout")
        with self.assertRaises(ledger.LedgerError):
            self.cp()

    def test_state_drift_is_detected(self):
        self.cp()
        path = ledger.task_dir(self.root, "checkout") / "STATE.md"
        path.write_text(path.read_text().replace("Baseline checkout tests passed", "Tests failed"))
        with self.assertRaises(ledger.LedgerError):
            ledger.load_state(self.root, "checkout")

    def test_explicit_goal_revision_invalidates_checkpoint(self):
        self.cp()
        ledger.revise_goal(self.root, "checkout", GOAL + "- AC3: Keyboard behavior preserved.\n", 1, "User requested keyboard support")
        report = ledger.doctor(self.root, "checkout")
        self.assertTrue(any("Goal changed" in warning for warning in report["warnings"]))
        self.assertEqual(report["goal_revision"], 2)
        self.assertEqual(ledger.load_goal(self.root, "checkout")[1]["criteria"], ["AC1", "AC2", "AC3"])

    def test_goal_revision_conflict_is_safe(self):
        with self.assertRaises(ledger.LedgerError):
            ledger.revise_goal(self.root, "checkout", GOAL, 0, "User clarified scope")
        self.assertEqual(ledger.load_goal(self.root, "checkout")[1]["revision"], 1)

    def test_explicit_repair_archives_damage(self):
        path = ledger.task_dir(self.root, "checkout") / "GOAL.md"
        path.write_text(GOAL.replace("one order", "two orders"))
        ledger.repair(self.root, "checkout", "goal", GOAL, 1, "Restored the user's one-order requirement")
        self.assertEqual(ledger.load_goal(self.root, "checkout")[0], GOAL)
        history = list((path.parent / "history").glob("*-damaged-goal.md"))
        self.assertIn("two orders", history[0].read_text())

    def test_state_repair_preserves_revision_order(self):
        self.cp()
        path = ledger.task_dir(self.root, "checkout") / "STATE.md"
        path.write_text(path.read_text().replace("Baseline checkout tests passed", "Unverified tests"))
        ledger.repair(self.root, "checkout", "state", STATE, 1, "Reconciled against the saved verification output")
        self.assertEqual(ledger.load_state(self.root, "checkout")[0]["revision"], 2)

    def test_bounds_and_required_sections(self):
        with self.assertRaises(ledger.LedgerError):
            self.cp(text=STATE + "x" * 7000)
        with self.assertRaises(ledger.LedgerError):
            self.cp(text=STATE.replace("## Next actions", "## Missing"))
        with self.assertRaises(ledger.LedgerError):
            ledger.validate_goal(GOAL + "\n## Objective\nNew conflicting objective\n")
        with self.assertRaises(ledger.LedgerError):
            ledger.validate_goal(GOAL + "- AC1: duplicate id\n")

    def test_completion_requires_current_evidence_for_every_criterion(self):
        evidence = {"AC1": {"result": "pass", "evidence": "test_checkout.py output"},
                    "AC2": {"result": "pass", "evidence": "existing suite output"}}
        with self.assertRaises(ledger.LedgerError):
            ledger.set_status(self.root, "checkout", "complete", "", evidence)
        self.cp()
        with self.assertRaises(ledger.LedgerError):
            ledger.set_status(self.root, "checkout", "complete", "", {"AC1": evidence["AC1"]})
        ledger.set_status(self.root, "checkout", "complete", "", evidence)
        self.assertEqual(ledger.load_goal(self.root, "checkout")[1]["status"], "complete")

    def test_nonactive_goal_does_not_restart_work(self):
        ledger.set_status(self.root, "checkout", "paused", "User requested pause")
        output = self.event("SessionStart")["hookSpecificOutput"]["additionalContext"]
        self.assertIn("do not resume", output)
        self.assertIsNone(self.event("PostToolUse"))

    def test_claude_precompact_writes_handoff_without_inventing_state(self):
        self.cp()
        self.event("PostToolUse")
        output = self.event("PreCompact")
        self.assertIsInstance(output, str)
        self.assertLess(len(output), 10000)
        handoff = (ledger.task_dir(self.root, "checkout") / "HANDOFF.md").read_text()
        self.assertIn("Regression test not yet written", handoff)
        self.assertIn("Tool events since this session's checkpoint: 1", handoff)
        self.assertEqual(ledger.load_state(self.root, "checkout")[0]["revision"], 1)

    def test_codex_precompact_is_silent_then_sessionstart_restores(self):
        ledger.bind(self.root, "checkout", "codex", "codex-chat")
        self.cp()
        self.assertIsNone(self.event("PreCompact", host="codex", session="codex-chat"))
        output = self.event("SessionStart", host="codex", session="codex-chat", source="compact")
        self.assertEqual(output["hookSpecificOutput"]["hookEventName"], "SessionStart")
        self.assertIn("Fix the checkout race", output["hookSpecificOutput"]["additionalContext"])

    def test_repeat_prompt_deduplicates_state_but_compaction_restores(self):
        self.cp()
        self.assertIsNotNone(self.event("UserPromptSubmit"))
        self.assertIsNone(self.event("UserPromptSubmit"))
        self.event("PreCompact")
        self.assertIsNotNone(self.event("SessionStart", source="compact"))

    def test_checkpoint_resets_reminder_counter(self):
        for _ in range(19):
            self.assertIsNone(self.event("PostToolUse"))
        self.assertIsNotNone(self.event("PostToolUse"))
        self.cp()
        binding = ledger.read_json(ledger.session_path(self.root, "claude", "chat-a"))
        self.assertEqual(binding["tools"], 0)

    def test_stop_guard_optin_and_no_recursion(self):
        self.assertIsNone(self.event("Stop"))
        ledger.write_json(self.root / ledger.STORE / "config.json", {"stop_guard": True})
        self.assertEqual(self.event("Stop")["decision"], "block")
        self.assertIsNone(self.event("Stop", stop_hook_active=True))

    def test_subagent_cannot_mutate_parent_counter(self):
        self.assertIsNone(self.event("PostToolUse", agent_id="child"))
        binding = ledger.read_json(ledger.session_path(self.root, "claude", "chat-a"))
        self.assertEqual(binding["tools"], 0)

    def test_hook_outside_initialized_project_is_noop(self):
        with tempfile.TemporaryDirectory() as folder:
            self.assertIsNone(ledger.hook(Path(folder), "claude", {"session_id": "s", "hook_event_name": "PreCompact"}))
            self.assertEqual(list(Path(folder).iterdir()), [])

    def test_hook_protocol_accepts_realistic_stdin_and_no_unknown_task(self):
        event = {"cwd": str(self.root), "session_id": "chat-a", "hook_event_name": "SessionStart"}
        result = self.run_cli("--host", "claude", "hook", stdin=json.dumps(event))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("hookSpecificOutput", json.loads(result.stdout))
        bad = self.run_cli("--host", "claude", "hook", stdin="not-json")
        self.assertEqual(bad.returncode, 1)
        self.assertEqual(bad.stdout, "")

    def test_dirty_tree_warns_even_when_status_shape_is_unchanged(self):
        path = self.root / "README.md"
        path.write_text("first edit")
        self.cp()
        path.write_text("a very different second edit")
        self.assertTrue(any("dirty" in w for w in ledger.doctor(self.root, "checkout")["warnings"]))

    def test_head_change_warns(self):
        self.cp()
        (self.root / "new.txt").write_text("change")
        self.git("add", "new.txt")
        self.git("commit", "-qm", "new head")
        self.assertTrue(any("HEAD changed" in w for w in ledger.doctor(self.root, "checkout")["warnings"]))

    def test_index_is_selective_and_detects_staleness(self):
        result = ledger.build_index(self.root)
        self.assertEqual(result["indexed"], 1)
        found = ledger.lookup(self.root, "checkout contract", 5)["matches"]
        self.assertEqual(found[0]["path"], "README.md")
        self.assertFalse(found[0]["stale"])
        (self.root / "README.md").write_text("# Changed\n")
        self.assertTrue(ledger.lookup(self.root, "checkout", 5)["matches"][0]["stale"])

    def test_index_excludes_ignored_symlink_and_dependency_files(self):
        (self.root / ".gitignore").write_text("private.md\n")
        (self.root / "private.md").write_text("# Secret")
        (self.root / "linked.md").symlink_to(self.root / "README.md")
        (self.root / "node_modules").mkdir()
        (self.root / "node_modules" / "README.md").write_text("# Dependency")
        ledger.build_index(self.root)
        files = ledger.read_json(self.root / ledger.STORE / "index.json")["files"]
        self.assertEqual([f["path"] for f in files], ["README.md"])

    def test_code_fences_do_not_create_fake_headings(self):
        (self.root / "code.md").write_text("# Real\n```python\n# Fake\n```\n## Another\n")
        ledger.build_index(self.root)
        entry = ledger.lookup(self.root, "code", 5)["matches"][0]
        self.assertEqual([h["text"] for h in entry["headings"]], ["Real", "Another"])

    def test_path_escape_and_symlink_writes_are_rejected(self):
        with self.assertRaises(ledger.LedgerError):
            ledger.safe_path(self.root, "../outside")
        with self.assertRaises(ledger.LedgerError):
            ledger.task_dir(self.root, "../../outside")
        path = ledger.task_dir(self.root, "checkout") / "HANDOFF.md"
        path.unlink()
        path.symlink_to(self.root / "README.md")
        with self.assertRaises(ledger.LedgerError):
            ledger.render_handoff(self.root, "checkout", persist=True)
        self.assertIn("Checkout", (self.root / "README.md").read_text())

    def test_read_is_line_and_character_bounded(self):
        result = self.run_cli("read", "README.md", "--start", "3", "--lines", "1")
        self.assertEqual(result.stdout.strip(), "3: ## Contract")
        (self.root / "huge.md").write_text("x" * 13000)
        result = self.run_cli("read", "huge.md")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")

    def test_archive_is_bounded(self):
        for i in range(25):
            ledger.archive(self.root, "checkout", "handoff", str(i))
        files = list((ledger.task_dir(self.root, "checkout") / "history").glob("*-handoff.md"))
        self.assertEqual(len(files), ledger.HISTORY_KEEP)

    def test_file_only_recovery_cycle_keeps_goal_and_next_step(self):
        self.cp()
        self.event("PreCompact")
        ledger.bind(self.root, "checkout", "codex", "new-independent-chat")
        response = self.event("SessionStart", host="codex", session="new-independent-chat")
        text = response["hookSpecificOutput"]["additionalContext"]
        for required in ("one order", "Preserve the public API", "Regression test not yet written", "Add the regression test", "Debounce"):
            self.assertIn(required, text)
        self.assertLess(len(text), ledger.BOOTSTRAP_LIMIT)


if __name__ == "__main__":
    unittest.main()
