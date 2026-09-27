---
scope: project
severity: preference
triggers: []
domain: ''
title: "A3 H3: Observe body clauses instead of requirement status"
pr: 63
merged: 2026-09-20
branch: "feat/a3-observed-clauses"
---

# A3 H3: Observe body clauses instead of requirement status

What. In A3 round 3, H2 obtained 1 TP for v18, but v10 and v20 TPs were 0. Remove the two status fields for direct production/SW participation restriction from the existing company_size call, and have it return the original text of the body clause or null as the observation. Only connect null to absence if the existing conditions for target application, original text citation, and complete observation are passed. SW target application citation is limited to a continuous original text of within 120 characters. …

Why. In H2, out of 74 competitive cases, 15 were not_required, and out of 10 software_business=yes cases, 9 were software_participation=unknown. Separate the design that asked for the existence of a clause in the document and the legal necessity as a single status. Record the schema version in the execution settings so that past unknown/not_required are not reinterpreted as absence. The issue where SW citations combining multiple item table rows failed original text verification is also handled with short continuous citations.

Source. PR #63 · `feat/a3-observed-clauses`
