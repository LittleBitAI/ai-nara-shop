---
scope: project
severity: contract
triggers: ["화면", "vision", "프레임", "스크린", "캡처", "공유"]
domain: vision
title: "fix: 실측 점수 커밋에서 진단 화면 파일을 분리한다"
pr: 65
merged: 2026-09-20
branch: "fix/unmix-report-ui-from-score-record"
---

# fix: 실측 점수 커밋에서 진단 화면 파일을 분리한다

무엇. `f455753` 이 제목과 달리 두 가지를 같이 담았다 — 2026-09-20 제출 실측 기록과 진단 화면 작업이다. 내가 `git add` 한 것이 아니라 이미 index 에 올라가 있던 것이 `git commit` 에 딸려 왔다.

왜. | 파일 | 무엇 | | --- | --- | | `report.cmd` · `report.command` | 진단 화면 런처 | | `tools/report.py` | 그 런처 둘이 부르는 한 곳 | | `.gitattributes` | 위 런처들의 줄끝(`*.cmd` CRLF · `*.command` LF)을 위해 들어온 것 | `git rm --cached` 라서 작업본의 파일은 지워지지 않는다. 아직 커밋 안 된 나머지 진단 화면 작업(`web/` · `DESIGN.md` · `tools/build_report.py` · `.gitignore` · `docs/README.md`)과 같은 자리로 돌아가고, 그 작업이 끝났을 때 한 벌로 올린다. …

출처. PR #65 · `fix/unmix-report-ui-from-score-record`
