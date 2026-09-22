---
scope: project
severity: contract
triggers: ["화면", "vision", "프레임", "스크린", "캡처", "공유"]
domain: vision
title: "feat: 진단 화면이 파일럿 회차도 싣는다"
pr: 73
merged: 2026-09-21
branch: "feat/report-pilot-runs"
---

# feat: 진단 화면이 파일럿 회차도 싣는다

무엇. 파일럿 회차(`a5-scope-…`)를 `reports/runs/`에 등록해도 화면에 영영 안 실렸습니다.

왜. 빌더가 회차를 `reports/runs/*/dev/submission.csv`로 찾는데(`build_report.py:345`), 파일럿 회차는 그 파일이 없습니다. `company_size` 같은 한 단계만 GPU로 돌리고 나머지는 보관 원응답으로 재생하므로, 회차 하나가 (군 × 소비자)만큼의 CSV를 냅니다. ``` $ python -X utf8 tools/build_report.py --run a5-scope-1789959906563639676 error: a5-scope-1789959906563639676: dev/submission.csv 가 없다 ``` `*-hybrid.csv`가 제출물과 49열 동일합니다. 그래서 "한 항목 = CSV 하나"라는 화면의 전제를 그대로 두고, `<run-id>. …

출처. PR #73 · `feat/report-pilot-runs`
