---
scope: project
severity: preference
triggers: ["이력", "브랜치", "공개", "push", "train_unlabeled", "filter-branch", "master", "대용량"]
domain: 'git-history'
title: "chore: Publish pre-release development history excluding large files"
branch: "chore/pre-public-history"
---

# chore: Publish pre-release development history excluding large files

> **2026-09-19 Update — This branch no longer exists.** As the user decided to reduce remote branches to `main`, `chore/pre-public-history`(`2d5afad`) was deleted from both remote and local. The same 6 commits remain in local `chore/team-agent-setup`(`01d2124`), and it was confirmed via `git diff --stat` before deletion that the difference between the two branches was only `open/train_unlabeled.jsonl`. The only thing lost is one off-machine backup on GitHub. To recreate it, you can use the procedure below as `chore/team-agent-setup`.
> Source: `docs/tasks/public-push.md` "2026-09-19 Follow-up".

What. I created a copy of the 6 pre-release development history commits that were only local, removing only `open/train_unlabeled.jsonl` (790,790,220 bytes), and pushed it to `chore/pre-public-history` (tip `2d5afad`). The original `chore/team-agent-setup` (`01d2124`) and `master` (`4816cf6`) are kept as is locally. `main` was not touched, and the existing decision not to merge the large history branch into `main` is maintained.

Why. The fact that `master` and `chore/team-agent-setup` are "unmerged" in `main` is not because work is missing, but because a new snapshot commit was uploaded instead of a merge during the public push, causing the SHA to diverge. The evidence is `git diff --stat 01d2124 5506ca02`, and the differences are only the removed 790MB file and `reports/publication.json`. `master` is an ancestor of `chore/team-agent-setup`, and `main` is newer than that branch (`script.py` main 1068 lines vs branch 621 lines). Therefore, there was no work to reflect, and the only remaining choice was whether to leave the history on GitHub as well. Since what prevented publication was not the history but the blob within the history, I removed only that file using `git filter-branch --index-filter`. This decision is an update to `docs/tasks/public-push.md`'s "This file and the existing commit history containing it will not be publicly pushed" based on user judgment.

Verification: The difference between `2d5afad` and the original `01d2124` is one removed file, and the difference from the first public commit `5506ca02` is only `publication.json`. The remaining largest blob is `open/dev.jsonl` 8.3MB. Among the 6 history commits and 111 unique blobs, 107 text files were checked for secret keys and private absolute paths, and the 7 hit blobs all have the same OID as those currently in public `main`, so nothing new is exposed. The private absolute path in `reports/t2-*/manifest.json` has been in public `main` since before this push and is judged separately.

Source. `docs/tasks/public-push.md` "2026-09-17 Follow-up" · `chore/pre-public-history`
