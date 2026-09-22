---
scope: project
severity: preference
triggers: []
domain: ''
title: "A5: v18 범위 재검토 구현과 두 회차 결과 — 미채택"
pr: 80
merged: 2026-09-21
branch: "feat/a5-v18-scope-review"
---

# A5: v18 범위 재검토 구현과 두 회차 결과 — 미채택

무엇. 한 company_size 호출에서 별도로 추출한 scope_review를 v18에만 소비하는 후보를 구현하고, 실제 GPU 두 회차 결과를 등록했습니다. 후보는 미채택입니다. 2026-09-21 사용자 승인으로 실험 코드·결과 기록·장부 수정을 보관하기 위해 병합합니다. 운영 `script.py`는 변경하지 않습니다. …

왜. H3 저장 scope의 전역 교체는 v18 TP를 회복하면서 v10 FP도 늘렸습니다. 이번에는 동일 호출의 별도 범위를 v18에만 소비해 이를 분리하는 가설을 시험했습니다. 실제로는 199건에서 scope/review가 같고 1건은 competitive→unknown으로 보류돼 새로운 TP가 생기지 않았습니다. Macro 차이는 재검토 소비가 아닌 기존 필드 변화와 추론 변동을 포함합니다.

출처. PR #80 · `feat/a5-v18-scope-review`
