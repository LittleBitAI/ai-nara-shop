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

무엇. 원응답 회차를 등록하니 같은 `script.py`(`2ad9ea8f`)의 측정이 세 개 더 생겼다.

왜. | 대조한 쌍 | 코드 | 바뀐 셀 | ΔMacro F1 | | --- | --- | ---: | ---: | | run3 `dev` ↔ `dev-debug` (같은 세션) | 같음 | 41 | -0.000008 | | run2 ↔ run3 | 같음 | 33 | -0.000044 | | run2 ↔ run3 기본 CSV | 같음 | 37 | +0.000023 | | run1 ↔ run2 기본 CSV | 다름 | 25 | -0.002532 | | run1 ↔ run3 | 다름 | 32 | -0.002576 | 셀 churn은 어느 쌍에서나 25~41개인데 그 Macro F1 영향이 300배 벌어진다. 같은 코드에서 셀이 더 많이 바뀌는데도 점수는 안 움직인다 — 뒤집힌 셀들이 상쇄되기 때문이다. …

출처. PR #22 · `fix/reproducibility-and-colab-wiring`
