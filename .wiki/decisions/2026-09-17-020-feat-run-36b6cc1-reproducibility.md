---
scope: project
severity: preference
triggers: []
domain: ''
title: "feat: register the 36b6cc1 run and pin down 0.0025 of run-to-run drift"
pr: 20
merged: 2026-09-17
branch: "feat/run-36b6cc1-reproducibility"
---

# feat: register the 36b6cc1 run and pin down 0.0025 of run-to-run drift

무엇. D0 회차를 `tools/register_run.py`로 등록했다.

왜. | | `654c556` | `36b6cc1` | 차이 | | --- | ---: | ---: | ---: | | 최종 dev Macro F1 | 0.220787711290 | 0.218255345011 | -0.002532366279 | | 같은 회차 기본 | 0.217530582480 | 0.214998216200 | -0.002532366279 | | v13 재검증 기여 | +0.0032571288102262 | +0.0032571288102262 | 0 | | 추가 호출 대상 | 200건 | 107건 | -46.5% | | 추가 추론 | 330.8초 | 110.7초 | -66.5% | | dev 전체 | 896.9초 | 694.8초 | -22. …

출처. PR #20 · `feat/run-36b6cc1-reproducibility`
