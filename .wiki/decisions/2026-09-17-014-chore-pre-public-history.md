---
scope: project
severity: preference
triggers: ["이력", "브랜치", "공개", "push", "train_unlabeled", "filter-branch", "master", "대용량"]
domain: 'git-history'
title: "chore: 공개 전 개발 이력을 대용량 파일만 빼고 공개한다"
branch: "chore/pre-public-history"
---

# chore: 공개 전 개발 이력을 대용량 파일만 빼고 공개한다

무엇. 로컬에만 있던 공개 전 개발 이력 6커밋을 `open/train_unlabeled.jsonl`(790,790,220 bytes)만
제거한 사본으로 만들어 `chore/pre-public-history`(tip `2d5afad`)로 push했습니다. 원본
`chore/team-agent-setup`(`01d2124`)과 `master`(`4816cf6`)는 로컬에 그대로 둡니다.
`main`은 건드리지 않았고, 대용량 이력 브랜치를 `main`에 merge하지 않는 기존 결정은 유지합니다.

왜. `master`와 `chore/team-agent-setup`이 `main`에 "미머지"인 것은 일이 빠져서가 아니라 공개 push 때 merge 대신 새 스냅샷 커밋을 올려 SHA만 갈라진 것입니다.
근거는 `git diff --stat 01d2124 5506ca02`이며 차이는 제거한 790MB 파일과 `reports/publication.json`
둘뿐입니다. `master`는 `chore/team-agent-setup`의 조상이고 `main`이 그 브랜치보다 새 것입니다
(`script.py` main 1068줄 대 branch 621줄). 그래서 반영할 일감은 없었고, 남은 것은 이력을
GitHub에도 남길지의 선택뿐이었습니다. 공개를 막던 것은 이력이 아니라 이력 안의 blob이므로
`git filter-branch --index-filter`로 그 파일만 뺐습니다. 이 결정은
`docs/tasks/public-push.md`의 "이 파일과 이를 포함한 기존 커밋 이력은 공개 push하지 않는다"를
사용자 판단으로 갱신한 것입니다.

검증: `2d5afad` 대 원본 `01d2124`의 차이는 제거한 파일 하나, 대 공개 첫 커밋 `5506ca02`의
차이는 `publication.json` 하나입니다. 남은 최대 blob은 `open/dev.jsonl` 8.3MB입니다.
이력 6커밋·고유 blob 111개 중 텍스트 107개를 비밀키·개인 절대경로로 검사했고, 적중한 blob
7개는 전부 현재 공개 `main`에 있는 것과 같은 OID라 새로 노출되는 것이 없습니다.
`reports/t2-*/manifest.json`의 개인 절대경로는 이 push 이전부터 공개 `main`에 있던 것이며
별도로 판단합니다.

출처. `docs/tasks/public-push.md` "2026-09-17 후속" · `chore/pre-public-history`
