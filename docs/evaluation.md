# Evaluation

## Deterministic coverage

The automated suite checks observable mechanics: task and host isolation, revision conflicts, goal drift, explicit repair, evidence requirements, bounded reads, ignored files, hook output contracts, one-shot Stop behavior, generated manifests and install/uninstall preservation.

The file-only recovery fixture starts with a goal and checkpoint, runs a PreCompact event, then binds another host/session and runs SessionStart. It checks that the objective, constraints, unresolved verification, failed approach and next step survive without a transcript. This is a protocol test, not an LLM performance evaluation.

## Manual or model-driven comparison

For an accuracy claim, use matched repository snapshots and tasks with objective tests. Evaluate at least these arms:

1. Full available history, without Context Ledger.
2. Fresh session with only the task, code and normal host compaction.
3. Fresh session with Context Ledger's goal, checkpoint and retrieval tools.

At a common point, freeze the repository and preserve the agent-generated checkpoint. Restart independently for each arm. Include changed-goal and changed-worktree cases; a correct recovery must identify stale assumptions rather than blindly continue them. Use multiple tasks and repeats; report model, host versions, input/output tokens, tool calls, compactions, wall time, acceptance-test results and human corrections.

Do not score only whether the handoff mentions the right words. Score the subsequent code behavior, constraints preserved and evidence supporting completion. Include unsaved-information failures and noisy/irrelevant documentation.

## What has not been established

No benchmark gain, dollar saving, token-reduction percentage or general equivalence to full context is claimed. The repository includes mechanics tests and native packaging checks. Any future model-driven evaluation should publish its task fixtures, conditions and results separately.
