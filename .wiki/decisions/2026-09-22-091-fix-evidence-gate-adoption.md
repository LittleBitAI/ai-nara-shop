---
scope: project
severity: preference
triggers: []
domain: ''
title: "fix: Adopt evidence contract and v24 comparison axis to raise dev 0.591 to 0.609"
pr: 91
merged: 2026-09-22
branch: "fix/evidence-gate-adoption"
---

# fix: Adopt evidence contract and v24 comparison axis to raise dev 0.591 to 0.609

What. This PR adopts two rules. Both were measured with 0 GPU calls and playback of stored raw responses.

Why. | | Macro F1 | Difference | | --- | ---: | ---: | | Baseline | 0.591008188119 | — | | Evidence contract (commit 1) | 0.603889319192 | +0.012881 | | v24 comparison axis (commit 2) | 0.609274806721 | +0.005385 | | Total | | +0.018267 | `pytest tests/` Fixed order 394 passed. dev exceeded 0.6 for the first time. --- v24 is a comparison type without clauses. Until now, only the citations provided by the model were compared with the meta, and if there were no citations, there was nothing to check, so violations remained as they were. If the code directly compares the axis (contract method, budget section, regional restriction, industry) and cannot find a single discrepancy, it lowers it. v24 `5/36/3 → 4/12/4` (F1 0. …

Source. PR #91 · `fix/evidence-gate-adoption`
