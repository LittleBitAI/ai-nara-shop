---
scope: project
severity: preference
triggers: []
domain: ''
title: "feat: cover every item with 50 notices instead of paying 33 hours for 200"
pr: 28
merged: 2026-09-17
branch: "feat/a-label-subset"
---

# feat: cover every item with 50 notices instead of paying 33 hours for 200

무엇. `export --cover N --negatives M --truth <csv>` — 항목마다 양성 N건을 덮는 공고만 고른다. 탐욕 선택이고 동점은 ID 사전순으로 깨서 같은 입력이 같은 목록을 낸다(R15). 선택에만 정답을 쓰고 번들에는 넣지 않는다. 선택 방식·정답 hash·미달 항목을 manifest에 남긴다. `collect --truth-out` — 라벨이 있는 ID만 남긴 정답 부분집합 CSV. `tools/score.py`는 손대지 않는다. …

왜. 첫 실제 라벨링이 공고 1건에 303초 걸렸다. 200건×2모델 = 33.7시간이다. dev 200건 중 양성이 하나라도 있는 공고는 88건뿐이고 112건은 24항목 전부 0이다. Macro F1은 양성 클래스 지표라 그 112건은 오탐 정보만 준다. | 선택 | 공고 수 | 2모델 | | --- | ---: | ---: | | 항목당 양성 ≥1 | 11건 | 1.9h | | 항목당 양성 ≥3 + 무양성 15건 | 50건 | 8.4h | | 전량 | 200건 | 33.7h | 무양성 15건은 오탐 측정의 편향을 줄인다. 양성 있는 공고만 쓰면 "전부 1"이라고 답하는 라벨러가 잘해 보인다. 이 부분집합의 F1은 `654c556`의 dev 0.2208과 같은 축이 아니다 …

출처. PR #28 · `feat/a-label-subset`
