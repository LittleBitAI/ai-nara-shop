---
scope: project
severity: preference
triggers: []
domain: ''
title: "feat: register the 36b6cc1 run and pin down 0.0025 of run-to-run drift"
pr: 20
merged: 2026-09-17
branch: "feat/run-36b6cc1-reproducibility"
---

# feat: register the 36b6cc1 run and pin down 0.0025 of run-to-run drift

What. Registered the D0 run as `tools/register_run.py`.

Why. | | `654c556` | `36b6cc1` | Difference | | --- | ---: | ---: | ---: | | Final dev Macro F1 | 0.220787711290 | 0.218255345011 | -0.002532366279 | | Same run baseline | 0.217530582480 | 0.214998216200 | -0.002532366279 | | v13 re-validation contribution | +0.0032571288102262 | +0.0032571288102262 | 0 | | Additional call targets | 200 cases | 107 cases | -46.5% | | Additional inference | 330.8s | 110.7s | -66.5% | | dev total | 896.9s | 694.8s | -22. …

Source. PR #20 · `feat/run-36b6cc1-reproducibility`
