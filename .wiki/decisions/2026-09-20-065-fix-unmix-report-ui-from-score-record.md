---
scope: project
severity: contract
triggers: []
domain: ''
title: "fix: Separate diagnostic screen files from the measurement score commit"
pr: 65
merged: 2026-09-20
branch: "fix/unmix-report-ui-from-score-record"
---

# fix: Separate diagnostic screen files from the measurement score commit

What. `f455753` Contrary to this title, it contains two things — the 2026-09-20 submitted measurement record and the diagnostic screen work. It was not `git add` by me, but was already in the index and came along with the `git commit`.

Why. | File | What | | --- | --- | | `report.cmd` · `report.command` | Diagnostic screen launcher | | `tools/report.py` | A place called by those two launchers | | `.gitattributes` | Included for the line endings (`*.cmd` CRLF · `*.command` LF) of the above launchers | Because it is `git rm --cached`, the work files are not deleted. They return to the same place as the remaining uncommitted diagnostic screen work (`web/` · `DESIGN.md` · `tools/build_report.py` · `.gitignore` · `docs/README.md`), and will be uploaded as a set when that work is finished. …

Source. PR #65 · `fix/unmix-report-ui-from-score-record`
