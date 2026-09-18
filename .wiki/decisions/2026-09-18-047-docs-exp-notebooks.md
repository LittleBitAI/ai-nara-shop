---
scope: project
severity: preference
triggers: []
domain: ''
title: "docs: 실험 노트북 셋을 main에 둔다 — 브랜치에만 있으면 안 보인다"
pr: 47
merged: 2026-09-18
branch: "docs/exp-notebooks"
---

# docs: 실험 노트북 셋을 main에 둔다 — 브랜치에만 있으면 안 보인다

무엇. 실험 노트북 세 개를 `main`의 `notebooks/`에 둔다. 문서(노트북)만 옮긴다 — `script.py`·`tools/`·`tests/`는 안 건드린다. | 노트북 | 가리키는 브랜치 | 담당 항목 | | --- | --- | --- | | `exp-n1-absence-split.ipynb` | `exp/n1-absence-split` | v16·v18 | | `exp-n2-amount-band. …

왜. 세 노트북을 각자의 실험 브랜치에만 올려 뒀더니 **`main`을 보고 있는 작업 폴더에서 파일이 보이지 않았다.** 팀원에게 "이 노트북을 실행해 주세요"라고 할 수가 없다. 노트북이 실험 코드와 같은 브랜치에 있을 이유가 없다. 노트북이 하는 일은 `REPO_REF`로 실험 브랜치를 가리키는 것뿐이고 Colab이 그 브랜치를 직접 clone한다. 그러므로 노트북은 main, 코드는 브랜치가 맞다.

출처. PR #47 · `docs/exp-notebooks`
