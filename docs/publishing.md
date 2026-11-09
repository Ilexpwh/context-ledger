# Publishing

The public repository target is `Ilexpwh/context-ledger`. GitHub repository creation requires a signed-in web or API session; SSH authentication supports Git fetch and push but cannot create a repository.

For the first publication, create an empty **public** repository named `context-ledger` under `Ilexpwh` at [GitHub](https://github.com/new). Do not initialize it with a README, license or `.gitignore`: those files are already committed locally. Alternatively, use GitHub CLI after checking that its active account is `Ilexpwh`:

```sh
gh api user --jq .login
gh repo create Ilexpwh/context-ledger --public --description 'Local goals, compact handoffs and Markdown retrieval for Codex and Claude Code'
```

From the local repository root, confirm the SSH identity and remote:

```sh
ssh -T git@github.com
git remote -v
```

GitHub's successful SSH greeting should name `Ilexpwh`; the SSH check normally exits with status 1 because GitHub provides no interactive shell. If no `origin` exists, add it:

```sh
git remote add origin git@github.com:Ilexpwh/context-ledger.git
```

Inspect an existing remote before changing it. After the empty repository exists, publish the committed `main` branch over SSH:

```sh
git push -u origin main
```

For later updates, run the checks in `AGENTS.md`, review and commit the changes, then run `git push`. Do not force-push over unrelated remote history.

Once published, users can register the GitHub marketplace:

```sh
claude plugin marketplace add ilexpwh/context-ledger
claude plugin install context-ledger@context-ledger-marketplace
codex plugin marketplace add ilexpwh/context-ledger
codex plugin add context-ledger@context-ledger-marketplace
```

Publishing to a host's public directory is a separate process from publishing this GitHub repository. No directory submission is part of this project setup.
