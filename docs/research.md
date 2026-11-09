# Research and design rationale

Reviewed 2026-11-09. This implementation is original; the projects below were studied for patterns, not copied or bundled. Findings from papers are not measurements of this plugin.

## Evidence and related projects

| Source | Relevant observation | Design choice here |
| --- | --- | --- |
| [You don't need long context, §2–5 and Appendix A](https://arxiv.org/html/2611.05306v1) | Frequent compaction and selective input reading preserve much of the tested task performance. Useful compaction retains what enables continuation. | Small state, separate durable goal, selective document reads and checkpoint-before-compaction workflow. |
| [Compact-Bench](https://arxiv.org/abs/2610.31710) | Specific compaction boundaries can damage coding continuations; retaining details and preserving successful continuation are different evaluation targets. | Keep exact evidence pointers and dead ends; test recovery behavior and avoid claiming universal accuracy preservation. |
| [Anthropic: effective context engineering](https://www.anthropic.com/research/effective-context-engineering-for-ai-agents) | Context must be actively curated; compaction and structured notes support extended tasks. | Bounded recovery packets with on-demand retrieval; no automatic loading of all memory. |
| [Anthropic: effective harnesses for long-running agents](https://www.anthropic.com/research/effective-harnesses-for-long-running-agents) | Agents benefit from persistent progress artifacts and incremental work between sessions. | Explicit acceptance criteria, verification evidence and a concrete next action. |
| [planning-with-files](https://github.com/OthmanAdi/planning-with-files) | Local planning files, task selection and recovery are a practical agent interface. | Human-readable files, explicit chat bindings and narrow skills; compare this existing project before adding another memory system. |
| [claude-mem](https://github.com/thedotmack/claude-mem) | Automatic observation capture and later context retrieval address persistent agent memory. | A smaller local-only approach: no transcript ingestion, database or extra model call. This sacrifices automatic semantic capture. |

## What follows from the paper, and what does not

The paper's EoCC pattern motivates periodic checkpointing. Selective file reading motivates the Markdown index. SAC motivates keeping a state that could support a fresh invocation after a short stretch. This package does **not** force one action per context, train the proposed semantic state-space model, or reproduce the paper's evaluation. Character budgets and reminder intervals are implementation defaults, not experimentally established optimal thresholds.

Separate goal revisions, host/session bindings, optimistic checkpoint revisions and filesystem integrity checks are engineering choices made for this package. They address practical failure modes beyond the paper's core experiment: goal drift, selecting another chat's task, overwriting newer state and trusting stale files.

## Host source of truth

- [OpenAI plugin packaging](https://developers.openai.com/plugins/build/plugins): portable manifest, compatibility overlay and marketplace layout.
- [OpenAI hooks](https://learn.chatgpt.com/docs/hooks): event schemas, trust, PreCompact and compact-time SessionStart behavior.
- [Claude plugin manifests](https://code.claude.com/docs/en/plugins-reference): component discovery and plugin-relative paths.
- [Claude hooks](https://code.claude.com/docs/en/hooks): event input/output and Stop recursion handling.
- [Claude skills](https://code.claude.com/docs/en/skills): skill loading, command arguments and session/path substitutions.
- [Claude marketplaces](https://code.claude.com/docs/en/plugin-marketplaces): local marketplace registration and distribution.

The implementations intentionally keep host-specific output separate. Current Context7 material and the official pages were checked; where summaries differed, the fetched official host documentation determined the adapter behavior.

## Tradeoffs

Maintaining a checkpoint costs time and tokens. Tool-count reminders are cheap but cannot see the actual remaining context budget. A conservative dirty-tree warning can be noisy but avoids presenting a Git status signature as proof of unchanged code. No transcript capture reduces accidental retention of sensitive input, but unsaved facts can be lost. The agent should checkpoint at meaningful milestones while it still has the necessary context.
