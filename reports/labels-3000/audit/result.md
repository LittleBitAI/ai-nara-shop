# Label audit — v18, v10, v11 on labels-3000 (2026-09-27)

Sample fixed before reading ([sample.json](sample.json), seed `20260928`): per item 15 cells labelled 1 and 15 labelled 0.
Each cell was read by Claude from the notice text, the 나라장터 registration fields and the catalogue lookup, against
the item definitions in `docs/items.md` and `reports/labels-600/item-guide.txt`. This is a model reading, not a human one.

## Result

| Item | Label 1 correct | Label 0 correct | Errors found |
| --- | --- | --- | --- |
| v18 | 14 of 14 decidable (1 unclear: registered price 1원) | 15 of 15 | none |
| v11 | 9 of 11 decidable (4 unclear) | 15 of 15 | 2 — catalogue service matched too widely (lecture video as 동영상제작서비스, "programme operation" as 행사기획) |
| v10 | 5 of 9 decidable (6 unclear) | 13 of 14 decidable | 2 notices say "중소기업자의 직접생산 여부를 확인합니다" (a requirement, so 0 by definition); 2 catalogue over-matches (programme operation, training video); 1 likely missed positive (통학버스 임차 = 통학운송서비스) |

The unclear v10/v11 cells are events and "programme operation" services where it is arguable whether the catalogue
행사기획 service applies (item guide: a programme the contractor runs is not that service unless the task is the service).

## A reading that was wrong, kept here so it is not repeated

At first the audit counted v18/v11 positives as errors when the registration field `조항호내용` names a size limit
("[판로지원법 시행령] 소기업,소상공인제한", "(소기업 소상공인 계약)", "(중소기업자)"). Dev gold says the opposite:
all 7 dev v18 positives, 5 of 6 v16 positives and 2 of 6 v11 positives carry such a clause. The violation is a notice
registered as size-limited whose body does not impose the limit. The body-reading labeler is right; no correction.

The v10 direct-production sentence is not corrected mechanically either: 3 of 7 dev v10 positives contain
"직접생산" wording (two post-award sanction sentences, one document list), so gold does not treat every mention as a requirement.

## The larger mismatch: 수의계약 (found after the audit)

Dev gold almost never marks a violation on a no-bid contract: 6 of its 153 positive cells sit on its 35 수의계약
notices (18% of notices; about 27 cells expected at an even spread) — v3, v4, v9, v17, v21, v24, one each. All 7 dev v18 positives are 제한경쟁.
The labeler does not follow this: 48% of the 2,000 are 수의계약, and 105 of their 175 v18 positives, 34 of 100 v1,
15 of 58 v20 and 14 of 32 v12 positives sit on them. The v18 cells above were graded by the item guide, which has no
수의계약 exclusion; under dev's convention most of the label-1 수의계약 cells would be 0.

So off-dev scoring now leaves 수의계약 notices out (`score_offdev.py --exclude reports/labels-3000/private-ids.txt`,
1,665 of the 3,600 off-dev notices). The current script scores 0.5006 on the 1,172 non-private notices of the
2,000 + diagnostic 200 (halves 0.4826 / 0.4722), against 0.436 on all of the 2,000.
Whether the server shares dev's convention is tested by the 9/27 submission (no positives on 수의계약 except
v3 v4 v17 v21 v24, dev-neutral on 19 saved dev response sets, removes 430 of 2,154 positive cells on the 5,500).

## What follows

- Trust stays as calibrated: v18 and v11 labels are better off dev than their dev-120 calibration suggested; v10 is the weakest.
- Read gains on v10 as direction only; audit the flipped cells of any v10 candidate (the targeted audit ①).
- The v18 recall pattern first read here ("registered as size-limited, body imposes no limit") does not hold up:
  the 42 missed cells are 수의계약 notices the script zeroes on purpose, in line with dev. It is not a rule candidate.
