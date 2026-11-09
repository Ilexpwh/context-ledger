# Validation record

Date: 2026-11-09. Version: 0.1.0.

Development environment: macOS, Python 3.14, Codex CLI 0.165.0, Claude Code 2.1.319.

## Checks

| Check | Result |
| --- | --- |
| Python unit/integration suite | 41 tests; covers state, recovery, hooks and installation |
| Configured hook execution | All 12 host/event combinations execute in an isolated project |
| Codex skill-creator validation | All four skills pass |
| Claude plugin manifest | Pass; no manifest errors or warnings |
| Claude marketplace manifest | Pass; no manifest errors or warnings |
| Claude native plugin loading | `--plugin-dir` inventory recognizes four skills, eight command aliases and six hook events |
| Codex native marketplace discovery | Recognizes `context-ledger@context-ledger-marketplace`, version 0.1.0, via command-local config overrides |
| Install/uninstall | Tested for both hosts, existing configuration, repeat install, customized-file refusal and paths with spaces/quotes |

Claude reports an optional missing-directory-icon warning. This does not prevent local plugin loading. No public-directory submission was attempted.

The native checks did not install the plugin into the user's global settings. The configured hook tests execute real shell commands with synthetic event JSON; they do not simulate an actual interactive model performing native compaction. Model-driven coding accuracy, token savings and long-running production behavior have not been benchmarked.

## Reproduce

```sh
python3 -m unittest discover -s tests -v
python3 scripts/validate.py
claude plugin validate .claude-plugin/plugin.json --json
claude plugin validate .claude-plugin/marketplace.json --json
claude --plugin-dir /absolute/path/to/context-ledger plugin details context-ledger
```

For read-only Codex discovery without registering a marketplace globally:

```sh
codex -c 'marketplaces.context-ledger-marketplace.source_type="local"' \
  -c 'marketplaces.context-ledger-marketplace.source="/absolute/path/to/context-ledger"' \
  plugin list --marketplace context-ledger-marketplace --available --json
```

The CI matrix is configured for Python 3.10 and 3.14 on Ubuntu and macOS. Those hosted runs will occur only after the repository is published; they are not counted as completed local checks.
