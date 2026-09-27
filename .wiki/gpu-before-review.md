---
scope: project
severity: landmine
triggers: ["리뷰\\s*(루프|요청|라운드)", "review\\s*(loop|round)", "라운드\\s*\\d", "머지\\s*허용", "(?<![a-z])PR(?![a-z])", "풀\\s*리퀘"]
reads: [docs/workflow.md]
sources: [reports/wiki-rag-pilot, reports/team-c/a8-v20-annex/results.md, reports/runs/colab-1790141677344456786, docs/tasks.md]
---

# Hypothesis PRs: Rounds first, review loops after effects are shown

Rule. If you open a PR for a hypothesis branch in this repository, the next instruction is not a review round, but a round.
If you only changed the steps after the model, run `tools/replay_run.py`; if you changed the prompt or schema, run the Colab round.
Issue the execution instruction (`run-request.md`) first. The review loop is conducted after the target item TP/FP/FN changes in the round. If it is a candidate for the steps before the model, measure churn with a second round of the same ZIP and even calculate the unlabeled utterance rate (re-run candidates have no churn, so there is no second round), and run it before merging or submitting. Collecting 6,000 unlabeled actual model samples is not a condition for the first round judgment. If there is no effect, leave only the report and close it — review round 0. The original source of the order is `docs/workflow.md` W5.

- Before the round, only check the activation (is the injection in the prompt, does the rule change the target cell?). This is a self-check and is not recorded as an independent review. Fixing it as a bug and running it again is only for when the activation check fails. If the activation is confirmed but the target cell or TP/FP/FN remains the same, the hypothesis is rejected.
- Code that goes into common infrastructure (observation, audit, re-run tools) that is not a hypothesis, and `main`/operational `script.py`, goes through review without exception. If a user asks to review first, that instruction takes precedence.

Why. For every hypothesis PR, about 6 rounds of reviews were conducted, only to be rejected in the round. PR #82 had 0 citations in 1,200 calls over two rounds, and B1 had v18 FN 6→6 — the model's response determined the result, and no round could change it.
A8 was rejected after 7 rounds of reviews and 10 rounds of observation wiring, with 0 notices changed in two rounds.

When violated. The most expensive step, the review, is used first on a hypothesis that will be discarded, and the round is delayed by several days.
