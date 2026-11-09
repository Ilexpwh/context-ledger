# Compatibility and troubleshooting

Compatibility baseline checked on 2026-11-09. The implementation targets the documented command-hook contracts and is tested with synthetic event fixtures. Host behavior can change; rerun native validation after upgrades.

| Surface | Integration |
| --- | --- |
| Codex CLI / desktop | Portable root plugin manifest plus `.codex-plugin` fallback, four skills, `hooks/codex.json` |
| Claude Code | `.claude-plugin/plugin.json`, native skill and command discovery, `hooks/hooks.json` |
| Standalone Codex skills | Project `.agents/skills`; optional `.codex/hooks.json` |
| Standalone Claude skills | Project `.claude/skills`; optional `.claude/settings.local.json` |
| Runtime | Python 3.10+; macOS/Linux; no third-party runtime packages |

The local host versions used during development are recorded in [VALIDATION.md](../VALIDATION.md). Full interactive model behavior is separate from manifest/protocol validation; no coding-accuracy claim follows from those checks.

## Different compaction contracts

Codex PreCompact ignores plain stdout. The Codex adapter writes the local handoff silently; `SessionStart(source=compact)` injects it before the continuation. Claude PreCompact command stdout becomes compaction guidance, so the Claude adapter also emits short instructions. Neither adapter attempts to make the hook itself run a new model call. [Codex](https://learn.chatgpt.com/docs/hooks), [Claude](https://code.claude.com/docs/en/hooks#precompact)

## Hooks do not fire

Confirm that the host loaded the plugin or project hook file, Python 3 is available, and the project has an initialized store. In Codex, review the actual hook definitions in `/hooks` or Settings → Hooks; changed bundled scripts require renewed trust. Managed host policy can disable non-managed hooks. The installer never bypasses host trust.

For standalone installs, restart after installation. If the project moved, reinstall so the absolute script paths are updated. Do not install both the native plugin and project hooks for the same project.

## The chat is unbound

This is intentional. Use `list`, then `bind --task TASK` with the actual host/session id. New, cleared or forked sessions may need a new binding. Claude plugin commands receive the session id through documented substitution; Codex normally exposes `CODEX_THREAD_ID`. If identity is unavailable, explicit `--task` commands work, but automatic restoration remains inactive.

## The handoff is stale

Run `resume`, which reads canonical goal/state records and a fresh repository snapshot. Inspect the relevant current files. Save a new checkpoint with verified facts; do not clear the warning by merely rewriting a timestamp. A dirty worktree warning is deliberately conservative and remains even after checkpointing.

## Integrity mismatch or interrupted update

Copy the damaged record to a separate local backup. Compare current user instructions, the handoff and saved history. Write a reconciled draft. Use the last recorded revision from `goal.json` or STATE.md's metadata:

```sh
python3 -I "$LEDGER" repair --task checkout-fix --kind goal --from-file work/reconciled-goal.md --expected-revision 1 --reason 'Restored the stated API constraint after an accidental direct edit'
python3 -I "$LEDGER" repair --task checkout-fix --kind state --from-file work/reconciled-state.md --expected-revision 3 --reason 'Reconciled saved facts against the current files and test output'
```

Repair archives the damaged original and increments the revision. It never silently edits a hash to bless unknown content. If STATE.md's metadata itself is lost, restore that metadata from a trusted backup before repair; do not fabricate a revision. If both files are damaged, repair the goal first, then the state. The first command may report the remaining state problem after successfully repairing the goal; inspect the new revision before retrying.

Goal updates replace two files separately. A crash between them is detected as an integrity mismatch on next read. Checkpoints use an atomic STATE.md replacement; HANDOFF.md can be regenerated. A process killed while holding `.context-ledger/.lock` can leave the lock directory behind: inspect `owner.json`, verify that the process is gone, and remove only that stale lock directory before retrying. Do not delete a live writer's lock.

## Installer refuses an upgrade

It found an existing unowned skill or a modified installed file. Preserve the customization and resolve the collision deliberately. Uninstall also refuses to delete modified files. Do not remove the receipt just to suppress the check. Run one installer per project at a time; installation is preflighted but not a multi-file filesystem transaction.

## Platform limits

The hook commands and standalone installer use POSIX shell quoting and `python3`; Windows has not been validated. Hosts that do not support the required hook events can still use the four skills and CLI manually. The package does not alter compaction thresholds, implement a token counter, provide a persistent autonomous loop, or train an SSSM.
