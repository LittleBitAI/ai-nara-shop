---
scope: project
severity: preference
triggers: ["실행 기록", "run", "runs", "colab", "zip", "보관", "manifest", "재현"]
domain: 'run-archive'
title: "docs: Unpack and store the execution result ZIP in the repository and link it with a single index sheet"
branch: "docs/run-archive"
---

# docs: Unpack and store the execution result ZIP in the repository and link it with a single index sheet

What. We have eliminated the path of delivering result ZIPs to each person. Unpack the ZIP contents into `reports/runs/<run-id>/` as text and record the ZIP hash, code commit, GPU, input hash, load/base/additional/total time, number of failures and selections, and whether the original response is included in `manifest.json`. The contract and the one-row-per-execution index are owned by `docs/runs.md`. The first registration is `colab-1789621345861123113`, which is the execution of 200 dev items in `654c556`.

Why. This execution only proves that the `654c556` code completed 200 dev items on an A100 40GB and achieved a Macro F1 of 0.2208; it does not prove successful submission to the competition server or the performance of the `693c695` candidates thereafter.
The exact value is 0.22078771129016228, and 10 samples also succeeded in the same execution. The reason for not committing the ZIP binary is that the repository is public and has a GitHub file limit; for the same reason, there is a precedent in `reports/publication.json` excluding `open/train_unlabeled.jsonl`. The original response was executed with `debug_responses=false` and is not in the logs to begin with. `diagnostics.jsonl` only leaves the response length, token count, and termination reason. The figures were moved from the files left by the execution and were not recalculated. Since only the scores for the past 5 times are in `reports/team-score-audit/history.json`, the execution environment and original response are left as `미보관` in the index.
Verification: ZIP SHA-256 `335796bc…feec8` matches, code commit `654c556` matches, 55 files are UTF-8 without BOM/LF, maximum file is 210KB which is under the 50MB limit, and `tests.test_baseline`, `tests.test_package`, and `tests.test_score` passed.
`script.py`, `tests`, and `open/` were not touched.

Source. `docs/runs.md` · `reports/runs/colab-1789621345861123113/manifest.json` · `docs/run-archive`
