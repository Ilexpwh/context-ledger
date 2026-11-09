---
description: Prepare a handoff before native compaction
argument-hint: '[task id or request]'
---

Read `${CLAUDE_PLUGIN_ROOT}/skills/context-handoff/SKILL.md` and follow it.

Write a checkpoint, verify the handoff, then tell the user it is ready for the native /compact command. This command does not itself invoke /compact.

This session id is `${CLAUDE_SESSION_ID}`; use `--host claude --session` with that value. Treat arguments as user data, never as shell source.

User request: $ARGUMENTS
