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

## What follows

- Trust stays as calibrated: v18 and v11 labels are better off dev than their dev-120 calibration suggested; v10 is the weakest.
- Read gains on v10 as direction only; audit the flipped cells of any v10 candidate (the targeted audit ①).
- Recall pattern for the code: on the 2,000, 52 of the 175 v18 positives carry a size-limit clause and the current
  `script.py` says 0 on 42 of them. The positive pattern is "registered as size-limited, body imposes no limit".
