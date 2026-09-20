---
scope: project
severity: preference
triggers: []
domain: ''
title: "fix: 실험 브랜치를 지웠으니 노트북도 main 을 보게 한다"
pr: 55
merged: 2026-09-18
branch: "docs/notebooks-after-integration"
---

# fix: 실험 브랜치를 지웠으니 노트북도 main 을 보게 한다

무엇. #54 에서 세 실험을 `main` 으로 합치고 `exp/n1-absence-split`·`exp/n2-amount-band`·`exp/n3-competitive-product` 를 지웠다. 그런데 노트북 셋이 그 브랜치를 가리키고 있었다.

왜. ```python REPO_REF = "exp/n1-absence-split" # 이제 없는 브랜치 ``` 팀원이 열고 실행하면 `git fetch` 에서 죽는다. `REPO_REF = "main"` 으로 바꾸고 맨 위 셀에 `EXP_ITEMS` 를 둔다. ```python REPO_REF = "main" # 실험은 전부 main 에 있습니다. 고치지 마세요 EXP_ITEMS = { "SPLIT_ITEMS": [], "BAND_ITEMS": ['v14', 'v15', 'v17'], "PRODUCT_ITEMS": [], } ``` clone 직후·패키징 직전에 그 값을 `script.py` 에 넣는다. 못 찾으면 `RuntimeError` 로 죽는다 …

출처. PR #55 · `docs/notebooks-after-integration`
