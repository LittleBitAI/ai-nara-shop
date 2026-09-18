---
scope: project
severity: preference
triggers: []
domain: ''
title: "docs: 워크트리에만 있던 결정 기록 8건을 main에 건진다"
pr: 41
merged: 2026-09-18
branch: "docs/harvest-decisions-030-038"
---

# docs: 워크트리에만 있던 결정 기록 8건을 main에 건진다

무엇. `.wiki/decisions/`에 2026-09-18 기록 8건(030·031·033·034·035·036·037·038)을 추가한다. 문서만 바뀐다. `script.py`·`tools/`·`experiments/`는 건드리지 않는다.

왜. PR이 40건 머지됐는데 main의 2026-09-18 결정 기록은 3건뿐이었다. 위키 훅이 Orca 워크트리(`anhinga`·`elkhorn`·`squirrelfish`) 안에서 Stop 이벤트에 기록을 만들었고, 그 워크트리들이 커밋 없이 남아 있어 main에 올라오지 않았다. 워크트리 정리를 하면 그대로 사라지는 자리였다.

출처. PR #41 · `docs/harvest-decisions-030-038`
