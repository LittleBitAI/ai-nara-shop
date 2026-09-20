---
scope: project
severity: preference
triggers: []
domain: ''
title: "docs: 이력 보관 브랜치를 지운 결정을 남긴다"
pr: 56
merged: 2026-09-18
branch: "docs/record-branch-cleanup"
---

# docs: 이력 보관 브랜치를 지운 결정을 남긴다

무엇. 원격 브랜치를 `main` 하나로 줄이면서 `chore/pre-public-history`(`2d5afad`)를 지웠다. 그 브랜치를 만든 2026-09-17 결정을 사용자 판단으로 갱신한 것이라 기록을 남긴다.

왜. 안 남기면 다음 세션이 "결정 기록은 push 했다는데 브랜치가 없다" 로 시작한다. GitHub 의 off-machine 백업 하나. 같은 6커밋이 로컬 `chore/team-agent-setup`(`01d2124`)에 있고, 지우기 전 확인했다. ``` $ git diff --stat chore/pre-public-history chore/team-agent-setup open/train_unlabeled.jsonl | Bin 0 -> 790790220 bytes 1 file changed ``` 차이는 그 파일 하나뿐이다. …

출처. PR #56 · `docs/record-branch-cleanup`
