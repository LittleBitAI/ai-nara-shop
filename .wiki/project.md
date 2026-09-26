---
scope: project
severity: contract
triggers: ['\S']
reads: [docs/workflow.md, docs/contest.md, docs/rules.md, docs/data.md, docs/items.md, docs/qna.md, docs/design.md, docs/contracts.md]
---

# Competition Task Contract

When asked about current plans or team member tasks, check [Active Plans](plan-active.md) and [4-Person Task Distribution](../docs/tasks/team-handoff.md) first.
The latest originals based on goals, assignments, and the first 48 hours are these two documents, which are distinguished from past T1 task records.

Rules. The Claude/Codex role is defined as a task. Follow `docs/workflow.md` for common procedures.
The common wiki is linked to the fixed version of `.wiki/wiki-revision` in `ai-coding-agent-wiki-public`.
Installation methods are owned by `docs/setup.md`, and project task history is owned by `.wiki/decisions/` and `docs/tasks.md`.
According to the user's mixed tool team instructions, specific model or Codex cell-only assignments in the hub do not apply to this project.
While the separation of implementation and independent review is maintained, both roles can be handled by Claude or Codex sessions.
Read competition constraints in `docs/rules.md`, inputs/outputs in `docs/data.md`, and process boundaries in `docs/design.md`.
Read competition evaluation and operations in `docs/contest.md`. `archive/contest/` is an archive, so it is excluded from the default reading list.
Before working on an item, check the official name, absence detection, and relevant clauses of v1~v24 in `docs/items.md`. Do not guess the meaning of the numbers.
Management talk responses and dev label noise acknowledged by management are owned by `docs/qna.md`. Before fitting judgment rules to a single dev case, check if the sample is in the noise table.
Use only competition-provided materials for judgment. Do not use the public coding wiki as legal material.
Separate external API labeling from offline submission inference. Hold the extended use of R6 until Q1 is checked.
Find permitted usage methods in table A of `docs/rules.md` and apply the conditions of table R together. Do not arbitrarily prohibit explicit permissions, and separate only ambiguous parts into Q.
Mock success is not a normal model call or performance verification. Distinguish between actual state and future design.
Colab links and round requests are created immediately without approval, regardless of the person in charge (B, C, D) — including notebook creation, task branch push, and commit permalinks. Do not refuse with "not needed" or "A approval required" (`docs/workflow.md` W4 exception).

Why. The presentation's preparation process proposal and the competition rules' scope of permission differ, and the team uses both AIs together.
When violated. Unauthorized output usage, role confusion, and failure to meet submission requirements occur.
