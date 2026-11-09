# Publish when ready

The intended public repository is `ilexpwh/context-ledger`. Repository creation and pushing are deferred. The local repository contains the plugin and marketplace metadata; those URLs do not imply that a remote repository already exists.

After signing GitHub CLI into `ilexpwh`, check the active login before creation:

```sh
gh api user --jq .login
gh repo create ilexpwh/context-ledger --public --source=. --remote=origin --push --description 'Local goals, compact handoffs and Markdown retrieval for Codex and Claude Code'
```

Run this from the repository root only when ready to publish. The command creates a public repository and pushes committed files. If the repository already exists, inspect it before adding a remote or pushing.

Once published, users can register the GitHub marketplace:

```sh
claude plugin marketplace add ilexpwh/context-ledger
claude plugin install context-ledger@context-ledger-marketplace
codex plugin marketplace add ilexpwh/context-ledger
codex plugin add context-ledger@context-ledger-marketplace
```

Publishing to a host's public directory is a separate process from publishing this GitHub repository. No directory submission is part of this project setup.
