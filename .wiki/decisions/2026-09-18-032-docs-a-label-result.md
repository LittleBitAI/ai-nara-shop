---
scope: project
severity: contract
triggers: ["대화\\s*(모델|프롬프트|응답|생성)", "응답\\s*(정책|수리|스키마)", "페르소나", "말투", "gemini", "openai"]
domain: dialogue
title: "docs: record the 33-notice result and open the prompt experiment as its own ticket"
pr: 32
merged: 2026-09-18
branch: "docs/a-label-result"
---

# docs: record the 33-notice result and open the prompt experiment as its own ticket

What. `docs/tasks/label-compare.md` — Actual measurement record of 50 Opus 5 executions. 33 completed, 17 CLI session limits, 179 seconds per case, Macro F1 0.6205 (do not compare with dev 0.2208 as it is a subset), distribution by item, rejected hypotheses. `docs/tasks/prompt-from-labels.md` — New ticket. Experiment to fix Gemma prompt v8, v14, and v15 questions based on 33 cases and measure the effect. Target items, measurement design, adoption/rejection criteria. …

Why. Opus 5 received the same notice, same legal snapshot, and same item definitions as Gemma but gave different answers. | Bundle | TP | FN | FP | | --- | ---: | ---: | ---: | | 11 items where Gemma had TP=0 for all 6 times | 21 | 14 | 4 | | Remaining 13 items | 31 | 7 | 22 | v8 3/3, v14 5/5, v15 3/3 — All were correct. Therefore, **the TP=0 of those items is not due to item difficulty but a flaw in the submission pipeline.** Unlabeled notices cannot make this distinction. Without a correct answer, it is impossible to know if Gemma is wrong or if the original answer is 0. The reason for separating the prompt experiment: that experiment is the ROI measurement for the entire labeling track. …

Source. PR #32 · `docs/a-label-result`
