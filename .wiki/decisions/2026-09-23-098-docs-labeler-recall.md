---
scope: project
severity: contract
triggers: ["기억", "memory", "회상", "mem0", "저장소.{0,4}기억"]
domain: memory
title: "v17 deletion gate — Labeler recall·6,000 unlabeled audits·operational reflection (v3 rejected)"
pr: 98
merged: 2026-09-23
branch: "docs/labeler-recall"
---

# v17 deletion gate — Labeler recall·6,000 unlabeled audits·operational reflection (v3 rejected)

What. A single line for verifying deletion-type candidates outside of dev. Merged what was split into #120 and #121 into this single PR. 1. Labeler recall — Blind labeling of all dev positives (19 notices) for v3, v4, v13, and v17 using Opus 5.5 · medium. TP cell hit v3 8/8 · v17 5/5 · v13 2/4 · v4 1/6 → Labeler's 0 is used only for confirming false positives in v3 and v17 2. …

Why. v17 is "restriction to SMEs for general goods under 100 million KRW" — allowing medium-sized enterprises is a violation. Restricting to small businesses and micro-enterprises for amounts under 100 million KRW is the form required by the Act on Facilitation of Purchase of Small and Medium Enterprise-Manufactured Products and Small Business-Manufactured Products, so it is not a violation. The model read citations like `소기업·소상공인 확인서` as allowing medium-sized enterprises and issued v17. `중소기업` contained in the names of laws (e.g., "Framework Act on Small and Medium Enterprises") are not qualification subjects, so they are masked. Citations where the article defines small and medium business operators, like `중소기업기본법 제2조에 따른 업체`, are kept. dev regeneration 11th round (original response CPU regeneration, GPU 0): v17 FP 108 removed · TP 1 lost · other items changed 0. The lost TP is PPS-DEV-035, where the model cited only `제한경쟁(소기업)` in the oldest round. …

Source. PR #98 · `docs/labeler-recall`
