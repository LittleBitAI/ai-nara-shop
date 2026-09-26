---
scope: project
severity: preference
triggers: []
domain: ''
title: "docs: wiki checkup excessive emphasis 8 cases cleanup · #142 post-merge outdated plan update"
pr: 144
merged: 2026-09-25
branch: "chore/a-wiki-lint"
---

# docs: wiki checkup excessive emphasis 8 cases cleanup · #142 post-merge outdated plan update

What. Remove 8 findings from the wiki checkup (`tool/lint.py --repo` · `tool/repo_lint.py --repo`), and update the outdated plan after #142 merge to the current state. | File | What | | --- | --- | | `reports/team-c/c6-dev-macro/README.md` · `RUN-REQUEST.md` | 8 cases of excessive emphasis (#139). Removed all 276·356 bold tags from outside the code. The reference key of the table becomes plain text like `| E |` …

Why. Two C6 documents had bold text in 61%·56% of prose lines (upper limit 15%), so the emphasis pointed to nothing. Bold tags containing paragraph labels·line breaks were also caught. `plan-active.md` was recording finished or incorrect items as current. - Recorded #133·#135·#137 as "server not submitted" per PR. Submission is the entirety of the `main` at that time. - Recorded #139 as "under review" (merged, rules are in `script.py` per #142). - Recorded submission ZIP as `submit-main-80e5d61`, and the item list as the pre-regeneration values of #141·#142. - "What to upload in the next submission" has been decided (`submit-main-0496ef0.zip`). …

Source. PR #144 · `chore/a-wiki-lint`
