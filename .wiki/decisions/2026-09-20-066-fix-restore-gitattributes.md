---
scope: project
severity: preference
triggers: []
domain: ''
title: "fix: 원래 있던 .gitattributes 를 되돌린다"
pr: 66
merged: 2026-09-20
branch: "fix/restore-gitattributes"
---

# fix: 원래 있던 .gitattributes 를 되돌린다

무엇. PR #65 에서 `.gitattributes` 를 진단 화면 작업으로 보고 통째로 뺐는데 틀렸다.

왜. `f455753` 은 그 파일을 만든 것이 아니라 이미 있던 19줄에 런처용 6줄을 더한 것이었다. `--stat` 의 `6 ++++` 를 새 파일 추가로 읽은 내 실수다. | 규칙 | 왜 | | --- | --- | | `* text=auto eol=lf` | 저장소 기본 줄끝 | | `/archive/contest/ -text` | 보관본 원본 바이트 보존 | | `/reports/runs/ whitespace=-trailing-space` | 회차 로그를 실행이 낸 바이트 그대로 | | `/compare/comparison.md whitespace=-trailing-space` | `compare_runs` 표의 열 정렬이 뒤 공백을 쓴다 | | `*.diff` · `*. …

출처. PR #66 · `fix/restore-gitattributes`
