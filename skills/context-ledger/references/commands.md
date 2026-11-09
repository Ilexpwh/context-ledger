# CLI reference

Examples use `LEDGER` for the absolute path to this skill's `scripts/ledger.py`.
Set it once with proper shell quoting. Global flags precede the subcommand.
CLI input files are UTF-8 and bounded. Use a file for multiline prose; never interpolate user prose into shell source.

## Initialize and bind

Create a goal file based on `../assets/goal.example.md`. Requirements:

- `## Objective`: the intended result, preserving significant user wording.
- `## Constraints`: scope and invariants, or `None specified.`
- `## Acceptance criteria`: unique `- AC1: ...`, `- AC2: ...` lines.
- Maximum 4,000 characters. Put large specs in a separate document and include a specific pointer, while retaining the essential contract here.

```sh
python3 -I "$LEDGER" --root /path/to/project init --task checkout-fix --goal-file /path/to/goal.md
python3 -I "$LEDGER" --root /path/to/project list
python3 -I "$LEDGER" --root /path/to/project --host codex --session "$CODEX_THREAD_ID" bind --task checkout-fix
```

For Claude, replace host and session with `--host claude --session ACTUAL_SESSION_ID`. The native Claude commands supply this id. Codex init/checkpoint can infer host/session from `CODEX_THREAD_ID`. Bind uses a hash of host plus id; no global active-task pointer exists. Worktrees keep independent stores. Binding a second chat to the same task is allowed, but concurrent checkpoint revisions must be merged explicitly.

The CLI discovers the nearest `.context-ledger` or Git worktree boundary. In non-Git projects, initialize at the intended project root. Pass `--root` for deterministic targeting.

## Checkpoint and resume

```sh
python3 -I "$LEDGER" --root /path/to/project status --task checkout-fix
python3 -I "$LEDGER" --root /path/to/project checkpoint --task checkout-fix --from-file /path/to/state.md --expected-revision 0
python3 -I "$LEDGER" --root /path/to/project handoff --task checkout-fix
python3 -I "$LEDGER" --root /path/to/project resume --task checkout-fix
python3 -I "$LEDGER" --root /path/to/project doctor --task checkout-fix
```

`--expected-revision` is the current checkpoint revision from `status`, not the goal revision. A mismatch refuses the write: read the newer state, merge facts, and retry deliberately. Do not retry blindly.

Checkpoint text has the six sections in `../assets/state.example.md`, maximum 7,000 characters. Use `None` in unused sections. The CLI wraps it with integrity metadata, writes STATE.md atomically, then renders HANDOFF.md. Do not directly edit generated STATE.md, GOAL.md or goal.json. Edit a draft, then use the CLI.

`handoff` only regenerates the wrapper; it does not create new semantic facts. `resume` renders from current source records, so it does not trust a stale HANDOFF.md. Dirty Git status is always a warning: the metadata signature cannot notice every content edit, nor does it validate test results.

## Goal changes and status

```sh
python3 -I "$LEDGER" --root /path/to/project goal-revise --task checkout-fix --from-file /path/to/revised-goal.md --expected-revision 1 --reason 'User added keyboard behavior to the acceptance criteria'
python3 -I "$LEDGER" --root /path/to/project goal-status --task checkout-fix --status blocked --reason 'Waiting for the test service credentials'
python3 -I "$LEDGER" --root /path/to/project goal-status --task checkout-fix --status active --reason 'User supplied the missing service access'
```

Goal revision preserves an earlier copy and invalidates the previous checkpoint's goal association. Write a fresh checkpoint after reconciling the change. A new revision becomes active and clears old completion evidence.

To complete, supply one verified evidence entry per current criterion:

```json
{
  "AC1": {"result": "pass", "evidence": "tests/checkout.test.ts: regression test passes; recorded run in work/verify.txt"},
  "AC2": {"result": "pass", "evidence": "Keyboard interaction checked in browser; result recorded in work/verify.txt"}
}
```

```sh
python3 -I "$LEDGER" --root /path/to/project goal-status --task checkout-fix --status complete --evidence-file /path/to/evidence.json
```

The evidence object records the agent's claims. It is not cryptographic attestation or a substitute for verification. User-requested pauses and cancellations remain effective regardless of unfinished criteria.

## Selective reading

```sh
python3 -I "$LEDGER" --root /path/to/project index
python3 -I "$LEDGER" --root /path/to/project lookup 'checkout contract' --limit 5
python3 -I "$LEDGER" --root /path/to/project read docs/checkout.md --start 40 --lines 60
```

Indexing excludes Git-ignored files, runtime memory, dependency/build directories and symlinks. In a non-Git folder, hidden directories are also excluded. The index is local metadata. A lookup searches paths and headings, returns at most 20 results, and marks changed/missing matches stale. For content search, use a focused `rg` query on selected documents. Do not read the full JSON index into context.

## Hooks and recovery

`.context-ledger/config.json` supports:

```json
{"remind_after_tools": 20, "stop_guard": false}
```

The interval is clamped to 5–200. `stop_guard: true` permits one checkpoint reminder on Stop when due, bounded by the host's `stop_hook_active` signal. It does not force goal completion. Leave it false when turn extension is undesirable.

## Explicit repair

If a goal or state hash fails, preserve the damaged files before attempting repair. Recover the last valid body from a handoff/history record and reconcile it against the current user request. Use the recorded revision in goal.json or STATE.md metadata, not a guessed revision:

```sh
python3 -I "$LEDGER" repair --task checkout-fix --kind goal --from-file /path/to/reconciled-goal.md --expected-revision 1 --reason 'Restored the user constraint after an accidental edit'
python3 -I "$LEDGER" repair --task checkout-fix --kind state --from-file /path/to/reconciled-state.md --expected-revision 3 --reason 'Reconciled with the working files and verification output'
```

Repair saves the damaged original in history and increments the revision. If STATE.md metadata is missing, restore it from a trusted backup first. Never conceal a mismatch by directly editing hashes. A killed writer can leave `.context-ledger/.lock`; inspect owner.json and confirm that the process is gone before removing that stale lock directory. Do not delete a live writer's lock.
