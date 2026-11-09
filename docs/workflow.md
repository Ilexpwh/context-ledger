# Working across context boundaries

## A practical cycle

Start with the user's exact outcome and nonnegotiable constraints. Translate completion into observable criteria without quietly narrowing the request. Put this in GOAL.md through `init`, then bind the current host and chat.

The agent works on one useful stretch, with small reads. It writes down changes only after they matter to future execution: an implementation decision, a verified result, a failed approach, a scope change or an upcoming context reset. This avoids turning memory maintenance into a second full conversation.

Before compaction, the agent saves a checkpoint. The PreCompact hook creates a recovery packet even if the agent forgot to request one explicitly. That packet clearly identifies the latest semantic checkpoint and does not manufacture new reasoning. SessionStart restores the saved task and flags stale work.

## Preserve the goal

Each task has its own goal and checkpoint revisions. Normal checkpoint writes cannot change the goal. `goal-revise` requires the expected goal revision and a recorded reason. If the user changes the task, the new goal invalidates the old checkpoint's goal association, requiring reconciliation.

`active`, `paused`, `blocked`, `cancelled` and `complete` are local task states. A non-active task is not an invitation for autonomous continuation. The current user request determines whether to resume it. The runtime never marks a goal complete merely because the agent stopped or compacted.

## Preserve evidence, not a diary

A useful checkpoint answers:

1. What is true now, and where can it be checked?
2. Which decisions constrain the next action?
3. Which checks ran, on which relevant state, and what remains unverified?
4. Which approaches failed and should not be repeated?
5. What exact action should happen next?
6. Which uncertainties or dependencies could change the plan?

Keep source paths and compact outcomes in state. Put logs, large plans and document extracts in files. Never turn an assumption into a verified fact during summarization.

## Cross-host handoff

Codex and Claude Code use the same project store. A second host runs `list`, selects the intended task, binds its own session id, and runs `resume` plus `doctor`. It does not inherit the first host's binding automatically.

If both agents write the same task, each supplies the checkpoint revision it read. Only a writer with the current revision succeeds. The other must reconcile the newer checkpoint. This prevents silent lost updates; it does not coordinate concurrent code edits. Use worktrees for independent edits.

## Finding documents

Build the index once, search paths/headings, then request useful line ranges. Refresh after documentation changes. The Markdown display is capped at 300 documents; the JSON index is bounded by a size budget and a 3,000-document cap. Oversized or unreadable Markdown is reported as skipped. Code retrieval remains a job for focused repository search.

## Sample terminal flow

Set `LEDGER` to the absolute bundled CLI path and keep cwd in the target project:

```sh
python3 -I "$LEDGER" init --task checkout-fix --goal-file work/goal.md
python3 -I "$LEDGER" --host codex --session "$CODEX_THREAD_ID" bind --task checkout-fix
python3 -I "$LEDGER" index
python3 -I "$LEDGER" lookup 'checkout contract'
python3 -I "$LEDGER" read docs/checkout.md --start 40 --lines 60
python3 -I "$LEDGER" status --task checkout-fix
python3 -I "$LEDGER" checkpoint --task checkout-fix --from-file work/checkpoint.md --expected-revision 0
python3 -I "$LEDGER" resume --task checkout-fix
```

Use the skill's bundled examples as a format guide, replacing the facts with actual observations. The CLI reference is [commands.md](../skills/context-ledger/references/commands.md).
