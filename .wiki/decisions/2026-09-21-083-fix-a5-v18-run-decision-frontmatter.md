---
scope: project
severity: preference
triggers: []
domain: ''
title: "fix: Round registration decision document front matter + A8 v20 appendix injection initiation document"
pr: 83
merged: 2026-09-21
branch: "fix/a5-v18-run-decision-frontmatter"
---

# fix: Round registration decision document front matter + A8 v20 appendix injection initiation document

What. Add front matter to two A5 v18 round decision documents and connect the A8 v20 article injection initiation document to the work queue and active plan. Maintain the round record body and operation code. A8 is an experiment that only adds the provision guidelines Article 2 and the original text of Appendix 1 to the existing company_size call. Maintain the schema, consumer, and observation gate, and compare the two rounds by swapping the order of the control/candidate in the same ZIP.

Why. Phase 1 statute lookup was completed with PR #81, but the injection effect is unmeasured. In the plan review, the following premise was corrected. 934 characters is the direct lookup confirmation value, and approximately 623 tokens is an estimate converted from character count. Since the baseline excess 0/200 calculation is not evidence of the safety of the company input, perform additional truncation with the actual tokenizer and check for visible body identity. The appendix contains the lower limits of 2 billion, 4 billion, and 8 billion, but it is not the entire v20 rule. The current consumer checks for SW business status, participation restriction guidance citation, and full observation, and does not directly compare amounts. In the fixed H4 mixed comparison, three false negatives are blocked by actual document omission, so the TP upper limit is 2. Without enforcing TP≥3, check the TP/FP improvement and out-of-scope regression of the two rounds. …

Source. PR #83 · `fix/a5-v18-run-decision-frontmatter`
