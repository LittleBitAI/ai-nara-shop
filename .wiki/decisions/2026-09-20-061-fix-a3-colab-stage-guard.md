---
scope: project
severity: preference
triggers: []
domain: ''
title: "fix: A3 Colab 검사 중단 수정과 완료된 dev 결과 복구"
pr: 61
merged: 2026-09-20
branch: "fix/a3-colab-stage-guard"
---

# fix: A3 Colab 검사 중단 수정과 완료된 dev 결과 복구

무엇. 공용/A3 Colab 노트북의 check_live가 SME 추가 분석을 생략한 행에서도 company_size의 v13 변경 권한을 인정하도록 수정합니다. 변경 가능 항목은 기존 extra_call_items에서 읽습니다. 소유권 없는 v13, 대상 밖 항목·ID, 모델 성공·선택 건수·설정·ZIP 검사는 유지합니다. 추론 코드와 A3 REPO_REF는 바꾸지 않습니다. …

왜. dev 200건이 정상 종료됐지만 PPS-DEV-184에서 company_size가 v13을 0→1로 바꾼 것을 옛 보호 조건이 차단했습니다. 이전 검사는 company_size의 v14~v18 변경만 확인해 v13 소유권 중첩을 놓쳤습니다. 해당 판정의 정답 여부와 파이프라인상 변경 권한은 별개입니다.

출처. PR #61 · `fix/a3-colab-stage-guard`
