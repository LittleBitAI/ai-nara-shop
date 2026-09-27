---
scope: project
severity: preference
triggers: []
domain: ''
title: "feat: underfitting items dev adaptation — #139 v18·v16·v11 porting · v13 citation repair — dev 0.7788 → 0.7925"
pr: 142
merged: 2026-09-25
branch: "feat/a-dev-fit-stack"
---

# feat: Underfitting items dev fit — #139 v18·v16·v11 porting · v13 citation repair — dev 0.7788 → 0.7925

What. Underfitting items (dev F1 less than 0.7) are raised to match dev according to confirmed 7. The rule set of #139 is moved to the current `main`, and two spots where the v13 model got it right but failed in citation verification were fixed. dev Macro 0.778789 → 0.792528 (+0. …

Why. Eight items below 0.7 from `main` reproduction were divided into those requiring GPU rounds and those that do not. I looked at the model P(1) and the subsequent reasoning for each error cell. v16·v18·v11 — #139 already showed effectiveness in reproduction, but because the base commit (`9038380`) was different, it did not attach directly to `main`. I moved it manually. 1·2 reproduces the same value as the 0.785092 measured by #141. v13 — FN `074`·`16` had main call P(1)=0.9988·0.9820 and the SME stage also produced `small_only`, but `verify_sme()` dropped it. - `074`: The original text was scattered across lines with numbers and parentheses like `「중소기업기본법 제 조제 항 … 」 2 2 「` due to PDF extraction. …

Source. PR #142 · `feat/a-dev-fit-stack`
