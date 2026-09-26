---
scope: project
severity: contract
triggers: ["런처", "게이트", "postgres", "마이그레이션", "ci"]
domain: infra
title: "feat: Re-evaluate five coverage gates as a bundle and pass A5"
pr: 69
merged: 2026-09-21
branch: "feat/a4-scope-gate"
---

# feat: Re-evaluate five coverage gates as a bundle and pass A5

What. Do not merge. For review only. `script.py` has not been fixed and is before/after adoption.

Why. `18f07e5` (dev 0.599316 / server 0.508414) was re-divided along the axis of "what is needed to reach 0.6". | | Max F1 achievable even with 0 false positives | | | --- | ---: | --- | | v6 0.400 · v9 0.417 · v10 0.421 · v13 0.421 · v24 0.222 | 0.667 ~ 0.909 | Reachable by reducing false positives only | | v11 0.400 · v18 0.200 · v20 0.200 · v23 0.222 | 0.500 · 0.250 · 0.333 · 0.333 | Unreachable — TP must be created anew | The first five (v6·v9·v10·v13·v23) were bundled and measured at once. …

Source. PR #69 · `feat/a4-scope-gate`
