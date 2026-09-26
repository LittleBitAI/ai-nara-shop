---
scope: project
severity: preference
triggers: []
domain: ''
title: "chore: add vite dependency cache to gitignore"
pr: 70
merged: 2026-09-20
branch: "chore/ignore-vite-cache"
---

# chore: add vite dependency cache to gitignore

What. `web/.vite/` remained untracked and was dirtying `git status`. It is a build artifact in the same location as `/web/node_modules/` and `/web/dist/`, but it was missing from the rules.

Why. ① The team is already running without committed vite caches. The cache actually used by the screen is `web/node_modules/.vite/deps`, and `/web/node_modules/` of `.gitignore:22` already ignores it. Practice is evidence. ② The `web/.vite/` that remained is empty. ``` web/.vite/deps/_metadata.json 146B optimized: {} chunks: {} web/node_modules/.vite/deps/_metadata.json 1101B optimized: { react, react-dom, ... } ``` `configHash` is also different (`c057bf73` vs `6eb5477c`). …

Source. PR #70 · `chore/ignore-vite-cache`
