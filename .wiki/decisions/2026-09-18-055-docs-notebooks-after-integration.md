---
scope: project
severity: preference
triggers: []
domain: ''
title: "fix: Since the experiment branch has been deleted, make the notebooks point to main"
pr: 55
merged: 2026-09-18
branch: "docs/notebooks-after-integration"
---

# fix: Since the experiment branch has been deleted, make the notebooks point to main

What. In #54, three experiments were merged into `main`, and `exp/n1-absence-split`, `exp/n2-amount-band`, and `exp/n3-competitive-product` were deleted. However, the three notebooks were still pointing to those branches.

Why. If a ```python REPO_REF = "exp/n1-absence-split" # 이제 없는 브랜치 ``` team member opens and runs them, they die at `git fetch`. Change them to `REPO_REF = "main"` and place `EXP_ITEMS` in the top cell. Immediately after ```python REPO_REF = "main" # 실험은 전부 main 에 있습니다. 고치지 마세요 EXP_ITEMS = { "SPLIT_ITEMS": [], "BAND_ITEMS": ['v14', 'v15', 'v17'], "PRODUCT_ITEMS": [], } ``` clone and just before packaging, insert that value into `script.py`. If not found, die with `RuntimeError` …

Source. PR #55 · `docs/notebooks-after-integration`
