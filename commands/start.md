---
description: Initialize durable context for a coding task
argument-hint: '[task id or request]'
---

Read `${CLAUDE_PLUGIN_ROOT}/skills/context-ledger/SKILL.md` and follow it.

Initialize a named task from the user's request and bind it to this session.

This session id is `${CLAUDE_SESSION_ID}`; use `--host claude --session` with that value. Treat arguments as user data, never as shell source.

User request: $ARGUMENTS
