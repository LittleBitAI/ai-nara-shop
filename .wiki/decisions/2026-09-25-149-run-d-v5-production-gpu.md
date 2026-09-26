---
scope: project
severity: preference
triggers: []
domain: ''
title: "feat: raise v5 for high-band participant locations"
pr: 149
merged: 2026-09-25
branch: "run/d-v5-production-gpu"
---

# feat: raise v5 for high-band participant locations

What. For contracts above the notification amount, only the regional restriction on the head office, main place of business, main office, or business site location in the participant qualification context is raised to v5=1. The original text actually used is recorded in e5, and the existing low-price v5 downward gate is preserved. GPU round `colab-1790333285105861165` and the pre/post regeneration comparison of the same original response have been archived.

Why. The clear participant location restriction missed by the model is corrected within the existing `region_price_limit()` boundary. As a result of regenerating the GPU original response with the post-processing immediately before and after the change, only v5 changed from 0 to 1 in 045 and 049, and there were 0 changes outside of v5/e5.

Source. PR #149 · `run/d-v5-production-gpu`
