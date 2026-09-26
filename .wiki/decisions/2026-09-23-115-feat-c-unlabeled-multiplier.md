---
scope: project
severity: contract
triggers: ["tts", "qwen", "음성", "목소리", "합성", "재생"]
domain: tts
title: "docs: C unlabeled utterance ratio (6,000 cases) — Only v14 is agreed upon by the three methods"
pr: 115
merged: 2026-09-23
branch: "feat/c-unlabeled-multiplier"
---

# docs: C unlabeled utterance ratio (6,000 cases) — Only v14 is agreed upon by the three methods

What. Did not run the iteration. CPU aggregation + saved response replay — 0 model calls · 0 GPU seconds.

Why. One unverified point that has blocked the adoption of candidate C throughout the session — "How often does this rule break outside of dev?" Replayed 200 dev cases with the same code (`14f03d1`) as the 2,000-case unlabeled iteration to place the numerator and denominator on the same scale. Since ten items were scanned at once, a 10-item correction was applied, and it does not rely on a single interval method. The evidence is 6,000 unlabeled cases. | Item | dev utterance | unlabeled | ratio | Katz simultaneous | score simultaneous | Holm p | Katz | score | agreement | dev TP/FP | | --- | ---: | ---: | ---: | --- | --- | ---: | --- | --- | --- | --- | | v10 | 12 | 369 | 1.03 | [0.46, 2.28] | [0.48, 2. …

Source. PR #115 · `feat/c-unlabeled-multiplier`
