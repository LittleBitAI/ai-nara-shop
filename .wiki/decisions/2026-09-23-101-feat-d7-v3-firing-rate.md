---
scope: project
severity: contract
triggers: []
domain: ''
title: "feat: v3 unlabeled utterance rate collector and Colab notebook (run results already reflected in #96)"
pr: 101
merged: 2026-09-23
branch: "feat/d7-v3-firing-rate"
---

# feat: v3 unlabeled utterance rate collector and Colab notebook (run results already reflected in #96)

What. A set of collector, notebook, and execution guide to measure the unlabeled utterance rate of the v3 gate. 3 code files + 1 inspection file. `script.py` is not touched — it has no effect on production decisions. | File | Content | | --- | --- | | `experiments/d7_collect_v3_firing.py` | Receives v3 judgment/citation via 24-item basic calls and runs the gate on top of it. Only the call step was changed from the shard/resume/contract framework of `a5_collect_facts.py` …

Why. `docs/workflow.md` W5 requires unlabeled utterance rate for dev reproduction candidates. Since v5/v6 only look at meta/original text, they finish on CPU, but the v3 gate reads the citations produced by the model — there is no model output for unlabeled, so the A4 §5 method does not work and a GPU run is required. I ran the actual run with this branch and the results are already included in PR #96 (`reports/runs/d7-v3-firing-1790141895014299603/`, gate multiplier 0.69, sample 1,000 cases). Since the execution code pointed to by `source.json` of that run is `c236a67` of this branch, this PR is to leave behind the code that makes that run reproducible. If not merged now, the execution code for the registered run will not be in the repository.

Source. PR #101 · `feat/d7-v3-firing-rate`
