---
scope: project
severity: preference
triggers: []
domain: ''
title: "docs: Record the remaining two items from the PR #39 review as D7 and D8 tickets"
pr: 40
merged: 2026-09-18
branch: "docs/d-review39-followups"
---

# docs: Record the remaining two items from the PR #39 review as D7 and D8 tickets

What. Two items from the PR #39 review remained only in the comments. Since the next session will not find and read the comments, I am moving them to the D table. #39 is already merged (`046dc86`) and this PR only changes the documentation.

Why. The participant qualification gate added by #39 prevents the original false positive raised by the review. There are three remaining spots, and the places to fix are different. 1. `_is_qualification_context` sees the header before the denial phrase on the same line and `break`. `※ 위 항목은 평가 배점이며 입찰참가자격을 제한하지 않는다` is caught by both regular expressions, so the sentence denying participant qualification becomes a pass. 2. It recognizes `참가자격` used within a sentence as a header. If `○ 입찰참가자격을 갖춘 자를 대상으로 다음과 같이 평가한다` is inserted, it cannot reach the header of the scoring table above. Changing the order does not close it either. 3. `NOT_QUALIFICATION` lacks `기술능력 평가` and `협상에 의한 계약 평가`. This was not created by #39 but is a blank space in the list used by v4. …

Source. PR #40 · `docs/d-review39-followups`
