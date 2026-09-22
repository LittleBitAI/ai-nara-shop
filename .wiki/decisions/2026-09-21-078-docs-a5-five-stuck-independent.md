---
scope: project
severity: preference
triggers: []
domain: ''
title: "docs: A5 다섯 항목 독립 분석과 v18 후속 착수서"
pr: 78
merged: 2026-09-21
branch: "docs/a5-five-stuck-independent"
---

# docs: A5 다섯 항목 독립 분석과 v18 후속 착수서

무엇. A4·H2·합본을 적용해도 v10·v13·v18·v20·v24의 F1이 그대로인 원인을 저장 원응답과 실제 문서 예산으로 추적했습니다. 다섯 항목 1,000셀이 전부 같고, 남은 오답 77셀·65공고의 원인은 항목별로 다릅니다. `five-stuck-analysis.md`: 단계별 원인, v24 업종 대조, H3 필드별 소비 분해, CPU/GPU 경계. `five_stuck_audit.py`·`five-stuck-audit. …

왜. v20의 PPS-DEV-132는 software_complete가 true인데 SW 적용 대상에서 막힙니다. v13은 baseline→SME→company의 합성으로 TP와 FP가 함께 되살아납니다. v10의 PPS-DEV-075는 직생 인용 누락이 아니라 제출서류를 참가자격 존재로 소비하는 의미 문제입니다. v24는 company 소비 대상이 아닙니다. 다섯을 하나의 실패로 묶으면 잘못된 곳을 고치게 됩니다. 다음 우선순위는 v18 적용범위입니다. H3 scope/인용만 교체한 CPU 진단에서 TP 2건 회복과 v10 FP 16건 증가가 함께 재현돼, 공유 사실을 전역 교체하는 대신 소비 효과와 기존 사실 훼손을 따로 검증하는 방법을 명시했습니다.

출처. PR #78 · `docs/a5-five-stuck-independent`
