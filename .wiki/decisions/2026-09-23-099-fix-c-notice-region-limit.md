---
scope: project
severity: preference
triggers: []
domain: ''
title: "fix: The local notification amount for v5~v7 is the regional restriction amount by ordering agency — v5 false positive 1 → 0"
pr: 99
merged: 2026-09-23
branch: "fix/c-notice-region-limit"
---

# fix: The local notification amount for v5~v7 is the regional restriction amount by ordering agency — v5 false positive 1 → 0

What. `script.py` `region_price_limit()` — Divide the regional restriction amount for local goods/general services by ordering agency. City/Province (excluding Sejong) 350 million KRW, others 500 million KRW. - The ordering agency is the first `[수요기관(…)]` token of `공고문` (`지방정부`·`광역자치단체` = City/Province, `기초자치단체` = City/County/District, unknown agency = 500 million KRW). - Sejong is determined only by two pieces of evidence tied to the ordering agency …

Why. The `고시금액` in the item name refers to different amounts in v5~v7 (regional restriction) and v2·v14~v16. Competition notice S6 supplemented the provided data with the Ministry of the Interior and Safety notification amount (350 million KRW, Ministry of the Interior and Safety Notification No. 2024-95) that was not in the legal package, and defined the local notification amount for v5~v7 as the regional restriction amount. Until now, the v5 gate used 230 million KRW for local areas as well, so regional restrictions in the 230 million KRW~500 million KRW range for local areas could be set as v5. Independent review round 8 (round 8 `머지 허용`). Since the Sejong judgment did not converge over six rounds, the evidence was fixed as two by user decision, and the service type word classification was also removed by user decision. Accepted limitations — Sejong notices without two pieces of evidence receive the City/Province amount, and real technical services registered as general services receive the general amount. …

Source. PR #99 · `fix/c-notice-region-limit`
