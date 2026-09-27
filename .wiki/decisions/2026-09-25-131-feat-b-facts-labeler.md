---
scope: project
severity: preference
triggers: []
domain: ''
title: "feat: B item fact labeler and v19 answer set outside dev (B11·B12)"
pr: 131
merged: 2026-09-25
branch: "feat/b-facts-labeler"
---

# feat: B item fact labeler and v19 answer set outside dev (B11·B12)

What. B11: Corrected the fact labeler for the four B items (v9·v19·v21·v24) to all 200 dev cases. The labeler only extracts facts from the notice, and the code performs the judgment (`experiments/b11_b_facts_verdict.py`·`b11_b_facts_v2_verdict.py`·`b11_fp_breakdown.py`). B12: Expanded the v19 answer set outside of dev …

Why. The final goal is to make the v1~v24 notice-answer pairs larger than the 200 dev cases, and this PR is a pilot to see the efficacy of that method with the B item. Correction (review stack-a round 1): The judgment code did not apply the predetermined "insufficient information=true is judgment 0", and it judged responses with incorrect formats (`PPS-DEV-066`) as they were. These are the values after fixing — the grades remain the same. | Item | v1 (Category judgment) | v2 (Original string, optimistic) | Conclusion | | --- | --- | --- | --- | | v9 | 0.286 | 0.308 | 14 out of the remaining 16 false positives are actual model names, but 0 in dev. It cannot distinguish any facts → Follow dev and exclude from expansion (user decision) | | v19 | 0.522 | 0. …

Source. PR #131 · `feat/b-facts-labeler`
