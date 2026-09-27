---
scope: project
severity: preference
triggers: []
domain: ''
title: "run: Unlabeled run (2,000 → 6,000 cases) — Establish the evidence for PR #115 in main"
pr: 120
merged: 2026-09-23
branch: "feat/unlabeled-d-run"
---

# run: Unlabeled run (2,000 → 6,000 cases) — Establish the evidence for PR #115 in main

What. This is a prerequisite for PR #115 (C unlabeled utterance ratio). All numbers in #115 come from the run outputs of this branch, and if that run is not in `main`, a reader of the report cannot follow the path to reproduce it. #115 §8 listed this as a prerequisite before merging, and the review pointed out the same thing.

Why. The work in this branch was not done by C. The unlabeled 2,000-case run was executed by A (`58af667`), and C merely read the output to calculate the ratio. C opening the PR on their behalf is to establish the evidence path for #115 in `main`. | | | | --- | --- | | Run | Unlabeled 2,000 cases, Colab A100 40GB, code `14f03d1` | | Result | 2,000/2,000 actual model success · Four bundles first attempt · Failure set F 0 · 8,436 seconds | | Reproduction | All four bundles `replay_run` playback are byte-identical to the run CSV | | New code | `tools/unlabeled_d.py` · `tools/unlabeled_sample. …

Source. PR #120 · `feat/unlabeled-d-run`
