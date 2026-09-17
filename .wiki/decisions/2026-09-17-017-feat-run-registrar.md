---
scope: project
severity: preference
triggers: []
domain: ''
title: "feat: register a Colab result ZIP pair with one command"
pr: 17
merged: 2026-09-17
branch: "feat/run-registrar"
---

# feat: register a Colab result ZIP pair with one command

무엇. `artifacts/inbox/`에 놓인 결과 ZIP 한 쌍을 한 명령으로 등록한다. 손으로 하던 언팩·대조·파일 작성을 없애되, 검증 실패는 반드시 실패로 끝낸다.

왜. ```powershell python -X utf8 tools/register_run.py --inbox artifacts/inbox --code-commit <커밋> ``` `reports/runs/<run-id>/`와 `manifest.json`, [색인](docs/runs.md) 한 행, `.wiki/decisions/<날짜>-NNN-run-<run-id>.md` 초안까지 쓴다. 커밋은 하지 않는다. - 수치는 실행이 남긴 파일에서 그대로 옮기고 재계산하지 않는다. 로그에 없으면 `null`, 점수가 없으면 색인 칸은 빈칸. - 색인은 같은 run-id 행이 이미 있으면 그 행을 채운다. `미보관` 행 5개가 중복되지 않게 하기 위함이다. …

출처. PR #17 · `feat/run-registrar`
