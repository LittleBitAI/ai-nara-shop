---
scope: project
severity: contract
triggers: []
domain: ''
title: "feat: Establish the first TP for v11·v12 with the competitor product gate"
pr: 57
merged: 2026-09-20
branch: "feat/a2-competitive-product"
---

# feat: Establish the first TP for v11·v12 with the competitor product gate

What. By having the code read the price ceiling of the `특이사항` notification catalog, the first TP in six rounds was established for v11·v12. It was reproduced with the same size in three sets of original responses. All are out-of-scope regressions 0. | Original Response | Macro F1 | Changed Cell | | --- | --- | --- | | `b113425` | 0.360884 → 0.396069 (+0.035185) | 6/4800 | | `99ebbf1` | 0.339492 → 0.375477 (+0. …

Why. The gate was the price ceiling of the notification `특이사항`. Catalog row 617 contains services (「Other Event Planning and Agency Services」 8014199001, 「Festival Planning and Agency Services」 9015189001), and festivals are "limited to an estimated price of less than 300 million KRW". `PPS-DEV-054` required direct production for that product name, but the estimated price is 327 million KRW — it is not a competitor product, but it required direct production, so it is a v12 violation. Until now, the code only passed this cell to the model as a string and did not compare it. The key to opening the gate was also not meta. Out of 21 dev training cases, 20 are general services, so `meta.세부품명번호목록` is empty. On the other hand, announcements requiring direct production almost always write the product name in that sentence — 1,244 out of 1,260 cases in 6,000 unlabeled cases (98. …

Source. PR #57 · `feat/a2-competitive-product`
