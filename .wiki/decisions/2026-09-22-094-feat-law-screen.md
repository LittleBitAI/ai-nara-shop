---
scope: project
severity: contract
triggers: ["화면", "vision", "프레임", "스크린", "캡처", "공유"]
domain: vision
title: "feat: Screen to view where the evidence clause of an item is in the statutes"
pr: 94
merged: 2026-09-22
branch: "feat/law-screen"
---

# feat: Screen to view where the evidence clause of an item is in the statutes

What. Added an `회차 진단 | 법령` tab to the header and set up the statute screen. `tools/build_report.py` uses `experiments/law_index.py` to resolve item table citations and create `web/public/laws.json`. There are 13 out of 23 statutes · 32 fragments, and each fragment carries the starting offset from the original statute text. `web/src/laws.jsx`: On the left, 24 items (the number at the back is `걸친 법령 수·조문 수`) and 13 cited statutes. …

Why. The item table only provides strings like `국가계약법 시행령 제12조 국가계약법 시행령 제21조`. One item does not fit into a single statute (v1 is four clauses of national/local enforcement decrees), and one enforcement decree Article 21 is shared by ten items. Humans were doing that comparison by eye, so this screen was requested. Do not look up the clauses again. Resolving the address is already done by `law_index.py`, and `tests/test_law_index.py` fixes all 31 citations. The screen only highlights the loaded positions — if a new parser is placed, the evidence splits in two places. The reason for carrying the offset is that "where is it" is the question of this screen. If you only provide a list in a 339,401-character document, the position is still not visible. …

Source. PR #94 · `feat/law-screen`
