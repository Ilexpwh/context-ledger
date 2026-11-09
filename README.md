# Context Ledger

Keep coding agents on the same goal across long sessions, compaction and agent handoffs. Context Ledger packages **four skills, eight Claude Code commands, and native Codex and Claude Code hooks** around small local Markdown records.

It uses Python 3.10+ and the standard library. No service, database, model API, embeddings or transcript ingestion is required. It is designed for macOS and Linux.

## How it works

```text
Durable goal + small working state + selected source ranges
                         ↓
                 inspect → act → verify
                         ↓
                save a new checkpoint
                         ↓
            compact / switch agent / resume
```

The runtime separates four responsibilities:

| Record | Purpose |
| --- | --- |
| `GOAL.md` | Objective, constraints and acceptance criteria; changed only through an explicit revision |
| `STATE.md` | Agent-written facts, decisions, verification, dead ends and next actions |
| `HANDOFF.md` | Generated recovery packet combining the goal, saved state and freshness warnings |
| `INDEX.md` | Local Markdown paths and headings for selective retrieval |

The skills maintain the semantic state. The hooks preserve and restore it. A PreCompact shell hook cannot recover reasoning that the agent never saved.

## Install

Use **one** installation method per host/project to avoid duplicate hooks. Installing the plugin alone does not create task memory; start a named task first.

### Claude Code plugin

From a local checkout:

```sh
claude plugin marketplace add /absolute/path/to/context-ledger
claude plugin install context-ledger@context-ledger-marketplace
```

For development without installation:

```sh
claude --plugin-dir /absolute/path/to/context-ledger
```

Restart Claude Code after installation. Review the installed commands and hooks with `/plugin` and `/hooks`.

### Codex plugin

From a local checkout:

```sh
codex plugin marketplace add /absolute/path/to/context-ledger
codex plugin add context-ledger@context-ledger-marketplace
```

Restart Codex and review/trust the hook definitions in `/hooks` or the desktop Hooks settings. Codex skips untrusted hooks. Releases with a Plugins UI but no `plugin add` command can install from the registered local marketplace there.

This repository is a Git-distributable marketplace, not a listing in OpenAI's public plugin directory. OpenAI currently excludes hook-bearing plugins from that directory; local/manual plugin installation is supported. [Official packaging guidance](https://developers.openai.com/plugins/build/plugins)

### Project-local skills and hooks

For projects that prefer checked-in configuration or hosts without plugin management:

```sh
python3 scripts/install.py --host codex --project /path/to/project --hooks
python3 scripts/install.py --host claude --project /path/to/project --hooks
```

Omit `--hooks` for skills only. The installer copies the complete skill bundle and merges its own hook groups into `.codex/hooks.json` or `.claude/settings.local.json`. It preserves other settings, refuses unowned file collisions, supports idempotent upgrades and refuses to overwrite customized installed files. Review generated files before committing project configuration. Installed hook commands use the absolute project path; reinstall after moving the project.

Remove this installation with the same project and host:

```sh
python3 scripts/install.py --host codex --project /path/to/project --uninstall
python3 scripts/install.py --host claude --project /path/to/project --uninstall
```

Uninstall removes only recorded, unchanged skill files and exact owned hook groups. It leaves task memory and unrelated configuration intact. Native plugins are removed with their host's plugin uninstall/remove command instead.

## Use it

In Codex:

```text
$context-ledger Track this checkout fix as task checkout-fix. Preserve the API and add regression coverage.
$context-handoff Save a verified checkpoint before compaction.
$context-resume Resume checkout-fix and verify the working tree first.
$context-index Find the checkout contract in the local docs.
```

In Claude Code:

| Command | Action |
| --- | --- |
| `/context-ledger:start` | Create a named goal and bind this chat |
| `/context-ledger:handoff` | Write a semantic checkpoint and handoff |
| `/context-ledger:resume checkout-fix` | Bind and recover the selected task |
| `/context-ledger:index checkout` | Index or search local Markdown |
| `/context-ledger:goal` | Inspect or explicitly revise scope |
| `/context-ledger:status` | Inspect the current task |
| `/context-ledger:doctor` | Check integrity and freshness |
| `/context-ledger:compact` | Prepare a handoff for the host's native `/compact` |

The `compact` command **prepares** a checkpoint; it does not invoke native compaction. You can then run `/compact`. The four skills are also available as native skill commands. Standalone installations expose the skills, not the eight plugin command aliases.

## What the hooks do

| Event | Behavior |
| --- | --- |
| `SessionStart` | Restore the bound goal and checkpoint; include freshness warnings after compaction |
| `UserPromptSubmit` | Inject changed state once; avoid repeating unchanged full handoffs |
| `PostToolUse` | Give a short checkpoint reminder every 20 tool events by default |
| `PreCompact` | Write HANDOFF.md and archive a bounded recovery copy |
| `Stop`, `SessionEnd` | Refresh the recovery wrapper without claiming a new semantic checkpoint |

Claude's PreCompact adapter also supplies concise compaction instructions. Codex's PreCompact adapter is silent and restores context through `SessionStart` with source `compact`. These are separate adapters because the host contracts differ. [Claude hooks](https://code.claude.com/docs/en/hooks), [Codex hooks](https://learn.chatgpt.com/docs/hooks)

Hooks do nothing in projects without a ledger. A new chat must select a task explicitly. Host/session bindings isolate chats, and checkpoint revisions reject conflicting concurrent updates. Use separate tasks or worktrees for independent work.

## Local layout and budgets

```text
.context-ledger/                # Git-ignored by its own .gitignore
├── config.json
├── INDEX.md
├── index.json
├── sessions/<host-id-hash>.json
└── tasks/checkout-fix/
    ├── GOAL.md                 # ≤ 4,000 characters
    ├── goal.json               # revision, status, digest and evidence records
    ├── STATE.md                # ≤ 7,000 characters, plus metadata
    ├── HANDOFF.md
    └── history/                # at most 20 files per record type
```

`resume` renders current source records rather than trusting the generated HANDOFF.md. Hook recovery output is bounded to 14,000 characters. These are **character limits, not token measurements**. This plugin neither changes model context windows nor forces a specific compaction threshold.

Configure reminders in `.context-ledger/config.json`:

```json
{"remind_after_tools": 20, "stop_guard": false}
```

Set `stop_guard` to true only if you want one checkpoint request before a turn finishes when the checkpoint is due. The host's recursion flag prevents repeated Stop continuations. This does not enforce task completion or override a user pause.

## Verification and limits

- Goal and state digests detect accidental drift. They do not authenticate a user instruction or defend against an attacker who can rewrite all local files.
- Completion requires an evidence record for every acceptance criterion. The runtime checks the records, not the truth of their claims.
- Dirty Git status and changed HEAD produce warnings. A status fingerprint is not a content hash of the entire working tree; relevant source and tests must be rechecked.
- Context quality still depends on the agent's checkpoints. The included file-only recovery tests do not establish a benchmark accuracy gain or measured token/cost savings.
- Runtime data stays local and ignored by default. Hooks do not read transcripts, call a model, execute saved instructions, make Git commits or send network requests. Do not put credentials in task memory.
- Symlink and parent-traversal paths are refused. These checks support normal local operation; they are not a sandbox against a hostile process racing filesystem writes.

See [the workflow guide](docs/workflow.md), [compatibility and troubleshooting](docs/compatibility.md), [research and design notes](docs/research.md), and [evaluation plan](docs/evaluation.md).

## Development

```sh
python3 -m unittest discover -s tests -v
python3 scripts/validate.py
claude plugin validate .claude-plugin/plugin.json
claude plugin validate .claude-plugin/marketplace.json
```

Edit `scripts/package.py` and regenerate manifests/commands with `python3 scripts/package.py`. The runtime has no dependencies outside Python's standard library. Skill metadata can additionally be validated with Codex's skill-creator validator.

MIT licensed. See [publishing](docs/publishing.md) for repository setup and the SSH push workflow.
