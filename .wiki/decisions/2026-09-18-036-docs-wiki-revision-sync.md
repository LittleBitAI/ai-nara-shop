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

What. Set the wiki reference commit of `docs/setup.md` to the same `bf7200dfc692f7f4ace483200f004ac64ae0352e` as `.wiki/wiki-revision`. It is one line of documentation. ```diff -- 위키 기준 커밋: `428a85d8e563f6d07e2a033b695474466f782b52`. +- 위키 기준 커밋: `bf7200dfc692f7f4ace483200f004ac64ae0352e``. The standard read by the machine is [. …

Why. The same paragraph stated "The standard read by the machine is `.wiki/wiki-revision`" and held a different SHA on the line right above it. If the value read by a human and the value read by a tool differ, the human side is wrong first. I checked the hub wiki to see which side was mismatched. | SHA | Value that was present | Location in the hub wiki | | --- | --- | --- | | `428a85d` | `docs/setup.md` commit version | Ancestor of HEAD (6 commits behind) | | `26e41d4` | Uncommitted changes remaining in the working tree | Ancestor of HEAD (intermediate commit) | | `bf7200d` | `.wiki/wiki-revision` | Actual HEAD | In other words, what is wrong is `. …

Source. PR #36 · `docs/wiki-revision-sync`
