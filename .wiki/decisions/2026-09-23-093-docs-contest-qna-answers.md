---
scope: project
severity: knowledge
triggers: ["QnA", "질의응답", "토크", "운영진 답변", "라벨 노이즈", "logprob", "동등 이상", "단위=기초", "제48조", "사업금액", "S7"]
domain: 'contest-rules'
title: "docs: Archive 17 management talk responses to S7 and move to docs/qna.md"
---

# Archive 17 management talk responses to S7

2026-09-23 A user provided 17 Dacon talk Q&As. There was no record of them anywhere in the repository. The original text is in `archive/contest/qna/` as bytes (S7), and the working copy is `docs/qna.md`.

There are four answers that can change the judgment.

| Answer | Source | Current Code |
| --- | --- | --- |
| Local area restriction amount — 350 million KRW for cities/provinces, 500 million KRW for Sejong/cities/counties/districts (Notice S6) | S7-17 | `fix/c-notice-region-limit` fixes it |
| Fixed threshold by logprob item is allowed via A4 post-processing, can be set as dev/self-label | S7-12 | Not used |
| v9 is not determined solely by the expression "equivalent or higher" | S7-4·14 | `V9_EQUIVALENT` drops v9 with that expression |
| The `단위=기초` of the region token is a city/county/district restriction | S7-15 | Operations does not read it. A4 candidate's v6 gate uses it, but it is unadopted as a bundle |

Also, the evaluation set has positive cases for all 24 items (S7-1). If you give up on one item, that item gets 0 points.

There are four samples where the management acknowledged dev label noise — `062` v24, `193` v13, `180` v9, `119` v10·v11.
`097` v18 only stated that the evidence could not be specified. Creating rules to match these cells is just creating another rule like the one seen in the 9/21 submission where it "wins in dev but loses on the server."
`132` is not noise — the management explained the principle supporting that label (S7-13). PR #100 review round 1 caught that the initial draft grouped this as noise.

The application of private contract for v16·v18 and the direction of the v24 regional restriction axis were not answered by the management either. They remain unconfirmed.
