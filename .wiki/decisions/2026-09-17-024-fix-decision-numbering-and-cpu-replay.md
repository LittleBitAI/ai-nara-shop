---
scope: project
severity: preference
triggers: []
domain: ''
title: "fix: stop the decision-record collision and add the CPU replay path"
pr: 24
merged: 2026-09-17
branch: "fix/decision-numbering-and-cpu-replay"
---

# fix: stop the decision-record collision and add the CPU replay path

무엇. 결정 기록 이름에서 일련번호를 뺀다. `tools/register_run.py`가 `<날짜>-run-<run-id>.md`로 쓰므로 공용 위키가 PR 번호로 캐 넣는 기록과 부딪힐 수 없다. 이미 만든 기록 3개를 옮기고, 제출 장부 기록은 실제 PR 번호 `019`로 맞췄다. 훅 생성본 6개는 LF로 바꿔 보존하고 중복 `014`는 지웠다. 고정 위키 리비전을 가드가 들어간 `bf7200d`로 올린다. `tools/replay_run.py`를 새로 만든다. …

왜. ### 결정 기록 충돌 공용 위키 `sync`가 손으로 쓴 결정 기록 013·015·016을 덮었다. `recorded()`가 frontmatter의 `pr:` 줄만 봐서 미기록 PR로 판정했고, 파일명 규칙이 같아 `write_text`가 그대로 덮었다. 작업 트리 변경이라 복구했고 커밋되지 않았다. 허브에는 가드를 달았다([PR #6](https://github.com/LittleBitAI/ai-coding-agent-wiki-public/pull/6) — 파일명 번호도 읽고, 있는 파일은 안 덮고, LF로 쓴다). 이쪽에서는 충돌 자체가 안 생기게 이름에서 번호를 뺀다. run-id는 그 자체로 유일하다. 훅은 쓸모가 있어 지우지 않았다. …

출처. PR #24 · `fix/decision-numbering-and-cpu-replay`
