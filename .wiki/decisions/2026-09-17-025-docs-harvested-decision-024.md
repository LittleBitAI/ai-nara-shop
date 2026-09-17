---
scope: project
severity: preference
triggers: []
domain: ''
title: "docs: 캔 결정 기록 하나를 커밋하고 가드가 선 것을 확인한다"
pr: 25
merged: 2026-09-17
branch: "docs/harvested-decision-024"
---

# docs: 캔 결정 기록 하나를 커밋하고 가드가 선 것을 확인한다

무엇. 공용 위키 `sync`가 PR #24에서 캔 결정 기록을 커밋한다.

왜. 허브 가드([PR #6](https://github.com/LittleBitAI/ai-coding-agent-wiki-public/pull/6))가 실제 저장소에서 서는지 확인했다. `sync.new_decisions`를 이 저장소에 직접 걸었다. ``` 새로 쓴 것: ['2026-09-17-024-fix-decision-numbering-and-cpu-replay'] 기존 파일 중 바뀐 것: 없음 ← 가드가 섰다 사라진 것: 없음 ``` 앞서 날아갔던 013·015·016도 그대로다. LF·no-BOM으로 쓴 것도 확인했다. 이것으로 직전 PR의 "미확인" 하나가 닫힌다. 그리고 이번 PR 본문에 `## 변경 요약`·`## 변경 이유` 절을 둔 결과가 눈에 보인다 …

출처. PR #25 · `docs/harvested-decision-024`
