---
scope: project
severity: preference
triggers: []
domain: ''
title: "feat: move your logprob threshold to the middle of your pass gaps — new pass replay +0.0220"
pr: 146
merged: 2026-09-25
branch: "feat/a-multi-replay-cuts"
---

# feat: Move your logprob threshold to the middle of your gate gaps — new gate replay +0.0220

What. Re-centres four S7-12 per-item logprob cuts (`ITEM_THRESHOLDS`) so each sits in the gap between the highest false positive and the lowest true positive over four GPU passes, instead of on the edge of the plateau fitted to one pass. …

Why. The two passes of `colab-1790318892216968298` (same code, same input) differ in 12 cells. Most sit on thresholded items right at the cut: `PPS-DEV-176` v9 is 0.99945 in one pass and 0.99883 in the other against a 0.999 cut; `PPS-DEV-066` v1 is 0.29 and 0.90 against 0.8; `PPS-DEV-191` v22 is 0.80 and 0.93 against 0.9. …

Source. PR #146 · `feat/a-multi-replay-cuts`
