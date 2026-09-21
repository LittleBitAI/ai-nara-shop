---
scope: project
severity: preference
triggers: []
domain: ''
title: "chore: vite 의존성 캐시를 gitignore에 넣는다"
pr: 70
merged: 2026-09-20
branch: "chore/ignore-vite-cache"
---

# chore: vite 의존성 캐시를 gitignore에 넣는다

무엇. `web/.vite/`가 미추적으로 남아 `git status`를 더럽히고 있었다. `/web/node_modules/`·`/web/dist/`와 같은 자리의 빌드 산출물인데 규칙에서만 빠져 있었다.

왜. ① 팀은 이미 커밋된 vite 캐시 없이 돌고 있다. 화면이 실제로 쓰는 캐시는 `web/node_modules/.vite/deps`이고, `.gitignore:22`의 `/web/node_modules/`가 이미 무시한다. 관행이 곧 증거다. ② 지금 남아 있던 `web/.vite/`는 비어 있다. ``` web/.vite/deps/_metadata.json 146B optimized: {} chunks: {} web/node_modules/.vite/deps/_metadata.json 1101B optimized: { react, react-dom, ... } ``` `configHash`도 다르다(`c057bf73` 대 `6eb5477c`). …

출처. PR #70 · `chore/ignore-vite-cache`
