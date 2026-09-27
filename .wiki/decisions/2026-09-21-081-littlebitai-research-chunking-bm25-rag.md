---
scope: project
severity: preference
triggers: []
domain: ''
title: "feat: RAG injection pipeline phase 1 — statute structure recognition lookup + v24 meta comparison"
pr: 81
merged: 2026-09-21
branch: "LittleBitAI/research-chunking-bm25-rag"
---

# feat: RAG injection pipeline phase 1 — statute structure recognition lookup + v24 meta comparison

What. Upgrade the RAG injection pipeline. This PR covers the first phase, which is the lookup. Nothing has been put into the prompt yet — since if the lookup is wrong, the injection will all be built on top of it, so it was created and reviewed before the injection.

Why. `artifacts/review/rag-pipeline-round-{1..9}{,-result}.md`. Round 9 results: `머지 허용` · No new findings. P1 per round: 2 → 3 → 4 → 3 → 2 → 1 → 2 → 0. All 21 cases were of the same type: "silently returning incorrect values." Five of them were regressions caused by my modifications. The most dangerous ones caught before adding the injection: | Defect | What would have happened at the injection stage | | --- | --- | | `국가계약법 시행령 제21조` → Article 21 of the Act | Injection based on the original text of another statute | | `제21조 제20항` (non-existent clause) → 2,646 characters of the full article | The entire article not requested as evidence | | `[별표1]` 420,768 characters cut to 11,267 characters by body reference → v23 …

Source. PR #81 · `LittleBitAI/research-chunking-bm25-rag`
