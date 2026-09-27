---
scope: project
severity: preference
triggers: []
domain: ''
title: "A3 H4: Extract qualification utterance roles before company grade"
pr: 64
merged: 2026-09-20
branch: "feat/a3-qualification-role"
---

# A3 H4: Extract qualification utterance roles before company grade

What. A3 round 4 failed to meet TP>0 for all three items with v10 4/7/3, v18 0/2/7, and v20 1/4/4. H4 extracts the role of the qualification utterance before the company grade in the existing company_size call. It distinguishes between actual participation qualifications, lists of submitted documents, legal citations, no mention, and unverified, and withholds qualification judgment if the role and company grade are contradictory. It does not force the checklist to unrestricted. …

Why. Even after the prose role instruction in H1, the H3 original response read the confirmation submission list as company grade participation qualifications. We are testing whether structuring the role and original text observation before the company grade reduces this confusion. There are no exceptions for announcement IDs or task names. No new calls are added. Verification: Passed 151 shared pipeline checks (37.833 seconds), passed Ruff and diff, CSV bytes before and after modification for 200 original responses each in original scope/H1/H2/H3 are identical, protected function AST is identical. Confirmed decompression mock 10 cases/49 columns and default entry failure without model. Confirmed notebook JSON, all code cell compilation, and fixed SHA and ZIP source match. Actual GPU effect, separate repeated churn for identical ZIP, 6,000 unlabeled cases, and time are unmeasured. …

Source. PR #64 · `feat/a3-qualification-role`
