---
scope: project
severity: preference
triggers: []
domain: ''
title: "docs: point the wiki pin at the revision the repo actually reads"
pr: 36
merged: 2026-09-18
branch: "docs/wiki-revision-sync"
---

# docs: point the wiki pin at the revision the repo actually reads

무엇. `docs/setup.md` 의 위키 기준 커밋을 `.wiki/wiki-revision` 과 같은 `bf7200dfc692f7f4ace483200f004ac64ae0352e` 로 맞춘다. 문서 한 줄이다. ```diff -- 위키 기준 커밋: `428a85d8e563f6d07e2a033b695474466f782b52`. +- 위키 기준 커밋: `bf7200dfc692f7f4ace483200f004ac64ae0352e`. 기계가 읽는 기준은 [. …

왜. 같은 문단이 "기계가 읽는 기준은 `.wiki/wiki-revision` 입니다" 라고 적어 두고 바로 윗줄에 다른 SHA 를 들고 있었다. 사람이 읽는 값과 도구가 읽는 값이 어긋나면 사람 쪽이 먼저 틀린다. 어긋난 쪽이 어디인지 허브 위키에서 확인했다. | SHA | 어디에 있던 값 | 허브 위키에서의 위치 | | --- | --- | --- | | `428a85d` | `docs/setup.md` 커밋본 | HEAD 의 조상 (6커밋 뒤짐) | | `26e41d4` | 작업 트리에 남아 있던 미커밋 변경 | HEAD 의 조상 (중간 커밋) | | `bf7200d` | `.wiki/wiki-revision` | 실제 HEAD | 즉 틀린 것은 `. …

출처. PR #36 · `docs/wiki-revision-sync`
