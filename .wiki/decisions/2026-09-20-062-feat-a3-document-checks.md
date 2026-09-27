---
scope: project
severity: preference
triggers: []
domain: ''
title: "A3 H2: Extraction of body requirements and verification of three-item TP"
pr: 62
merged: 2026-09-20
branch: "feat/a3-document-checks"
---

# A3 H2: Extraction of body requirements and verification of three-item TP

What. A3 H1 had 0 TP for v10, v18, and v20 in both rounds of the same ZIP. The next experiment excludes the clause content registered in the existing company_size call and extracts the direct production requirements and SW business/participation restrictions from the body, respectively. v10 and v20 connect the verified new facts to the CSV, and v18 uses the existing decision table. There are no new full-case calls. The dedicated notebook fixes the inference candidate cc7c9719b60b84f1fe6a713969ca886044066d75. …

Why. In round 2 as well, qualification citations not in the body were copied from the meta, and the first call had 0 cases for all three items. This is an experiment to separate cases where the document was not observed from cases where the requirements are not in the observed body. SW requires observation of the entire announcement/RFP, which is the specified location in Article 3② of the provision guidelines. It distinguishes between cases where only the end of the specification is cut off and cases where the announcement/RFP is missing.

Source. PR #62 · `feat/a3-document-checks`
