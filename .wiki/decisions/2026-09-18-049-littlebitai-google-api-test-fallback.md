---
scope: project
severity: contract
triggers: ["지연", "latency", "텔레메트리", "턴 조립", "api 조립"]
domain: api
title: "feat: mock 대신 API로 실제 Gemma 4를 불러 본다 — Colab 왕복 없이 표본을 쌓는다"
pr: 49
merged: 2026-09-18
branch: "LittleBitAI/google-api-test-fallback"
---

# feat: mock 대신 API로 실제 Gemma 4를 불러 본다 — Colab 왕복 없이 표본을 쌓는다

무엇. `tools/api_run.py` 추가. `script.py`를 모듈로 불러 같은 `run()`에 러너만 갈아 끼운다. 키가 있으면 Google AI Studio의 `gemma-4-26b-a4b-it`, 없으면 `MockRunner`로 떨어진다. `--mock`은 키가 있어도 mock을 강제한다. `script.py`는 4줄만 바뀐다. …

왜. Colab 왕복이 표본 쌓기의 병목이었다. 프롬프트 한 줄을 고칠 때마다 노트북을 열고 ZIP을 올리고 회차를 기다려야 해서, 몇 건만 보면 되는 확인도 회차 하나를 썼다. API는 같은 파이프라인을 로컬에서 몇 건씩 돌린다. 팀원 중 키가 없는 사람이 있으므로 mock을 버리지 않고 API 우선, 없으면 mock으로 떨어지게 했다. 세 실행을 기록이 구분해야 한다. API 회차를 `mock`으로 적으면 실제 호출이 없었던 것처럼 보이고, `live`로 적으면 R4 정상 호출을 한 것처럼 보인다. 둘 다 틀리다. 그래서 `mode`를 러너가 들고 있고 API 회차는 `model_success_count`가 0이다. …

출처. PR #49 · `LittleBitAI/google-api-test-fallback`
