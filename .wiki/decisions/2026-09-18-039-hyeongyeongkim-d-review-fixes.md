---
scope: project
severity: preference
triggers: []
domain: ''
title: "fix: PR #34 6 reviews — complex amount, v8 scoring table guard, clause boundary, stale hash"
pr: 39
merged: 2026-09-18
branch: "HyeongyeongKim/d-review-fixes"
---

# fix: PR #34 6 reviews — complex amount, v8 scoring table guard, clause boundary, stale hash

What. Fixes 6 items raised by the PR #34](https://github.com/LittleBitAI/ai-nara-shop/pull/34) review. #34 was merged in the meantime, so this is submitted as a follow-up PR.

Why. 1. Complex amounts were read 33% lower. `MONEY` captured `억` and `천만` separately and took `max`, causing `1억 5천만원` to be read as 100 million. If that value crosses the 1x boundary, the v3 rule drops the correct answer generation — this is the exact failure the rule was intended to prevent. It now consumes and adds the 100 million, 10 million, 10 thousand, and 1 won positions in a single match. Bare numbers without position markers are only treated as amounts when `원` is attached. Otherwise, it reads 10-digit detailed product codes and dates as amounts. With this fix, the amount of `PPS-DEV-078` is read, further reducing the v3 FP from 6 to 5. 2. There was no scoring table guard in the v8 `detect`. The sentence raised by the review was reproduced as is. …

Source. PR #39 · `HyeongyeongKim/d-review-fixes`
