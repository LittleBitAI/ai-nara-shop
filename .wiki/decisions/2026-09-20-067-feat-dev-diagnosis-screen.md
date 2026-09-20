---
scope: project
severity: contract
triggers: ["화면", "vision", "프레임", "스크린", "캡처", "공유"]
domain: vision
title: "feat: dev 200건을 항목별로 열어 보는 진단 화면"
pr: 67
merged: 2026-09-20
branch: "feat/dev-diagnosis-screen"
---

# feat: dev 200건을 항목별로 열어 보는 진단 화면

무엇. Colab 결과 ZIP을 넣으면 v1~v24 항목별 F1과, dev 200건 중 어디를 맞고 어디를 틀렸는지를 공고 원문까지 열어서 본다. 추론하는 화면이 아니라 이미 나온 결과를 보는 화면이다.

왜. ```powershell report.cmd # Windows (더블클릭도 됨) ./report.command # macOS (Finder 더블클릭) ``` ZIP 파일명은 회차마다 바뀌므로 어디에도 안 적는다. `--latest` 가 받은 함에서 가장 최근 `colab-results-<숫자>.zip` 을 고른다. 좌: 24항목이 F1 막대를 겸한 목록 / 우: 항목 스트립 → 공고 드릴다운 - 스트립 — 항목당 볼 것(FN·FP·TP)만 크게, TN 180칸 안팎은 접어 둔다 - 드릴다운 — 공고 원문 + 근거 하이라이트 + 모델 판정. …

출처. PR #67 · `feat/dev-diagnosis-screen`
