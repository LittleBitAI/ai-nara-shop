---
scope: project
severity: preference
triggers: []
domain: ''
title: "fix: 수집 시점에 꽂히는 submission 모듈에 카탈로그를 채운다"
pr: 74
merged: 2026-09-21
branch: "fix/replay-submission-catalogue"
---

# fix: 수집 시점에 꽂히는 submission 모듈에 카탈로그를 채운다

무엇. main 이 빨강입니다. #71 머지 직후부터 `tests/test_a5_scope_pilot.py` 하나가 전체 실행에서 깨집니다. 이 PR이 그것을 되돌립니다.

왜. ``` pytest tests/test_a5_scope_pilot.py 3 passed pytest 1 failed, 220 passed ``` 원인이 안 보이는 모양입니다. pytest는 검사를 돌리기 전에 모든 모듈을 수집하므로, 알파벳순으로 앞선 `test_a5_scope_pilot`이 실행될 때 이미 뒤쪽 파일의 모듈 수준 부작용을 받습니다. `tests/test_replay_run.py:15`가 모듈 수준에서 두 번째 script 모듈을 `submission` 이름으로 꽂습니다. ```python SCRIPT = replay_run.load_module(ROOT / "script.py", "submission") # _PRODUCTS == 0 ``` 후보들은 재생 대상 모듈을 그 이름으로 찾습니다. …

출처. PR #74 · `fix/replay-submission-catalogue`
