---
scope: project
severity: preference
triggers: []
domain: ''
title: "fix: correct the drift conclusion and wire the diagnose tool into the bundle"
pr: 22
merged: 2026-09-17
branch: "fix/reproducibility-and-colab-wiring"
---

# fix: correct the drift conclusion and wire the diagnose tool into the bundle

What. Registering the original response round created three more measurements of the same `script.py`(`2ad9ea8f`).

Why. | Compared pair | Code | Changed cells | ΔMacro F1 | | --- | --- | ---: | ---: | | run3 `dev` ↔ `dev-debug` (same session) | Same | 41 | -0.000008 | | run2 ↔ run3 | Same | 33 | -0.000044 | | run2 ↔ run3 base CSV | Same | 37 | +0.000023 | | run1 ↔ run2 base CSV | Different | 25 | -0.002532 | | run1 ↔ run3 | Different | 32 | -0.002576 | Cell churn is 25~41 in any pair, but the Macro F1 impact varies by 300 times. Even though more cells change in the same code, the score does not move — because the flipped cells cancel each other out. …

Source. PR #22 · `fix/reproducibility-and-colab-wiring`
