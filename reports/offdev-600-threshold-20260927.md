# Off-dev 600 logprob threshold measurement — 2026-09-27

## Reproducibility gate

The GPU source was the supplied archive unpacked at
`artifacts/offdev-600-1790471557297701344/`; it was not rerun.  Its two
shards cover the committed diagnostic 200 then sealed 400 ID order (600
unique IDs).  CPU replay of that fixed order produced 600 rows and matched
the archived combined CSV byte-for-byte:

- original/replayed SHA-256: `9d282a325981d3f17cfaf2d093a90279d750cd16a4a5c2d2a7de3d7ab1d87cb3`
- checkpoint: `artifacts/offdev-600-1790471557297701344/postflight-final.json`
- `identical`: `true`

The reproduction mismatch was solely CSV line terminators: the Colab
`script.write_csv` output uses the `csv.DictWriter` default CRLF, while
`replay_run.to_csv_bytes` forced LF.  The replay serializer now follows the
writer contract.

## Measurement

`tools/tune_offdev_thresholds.py` replayed saved `item_p1` values only; no
model call occurred.  It compared the established S7-12 grid plus already
configured cuts.  v9/v24 remain fixed because their off-dev labels are blank.

| Measurement | Macro F1 |
| --- | ---: |
| Current thresholds | 0.471322 |
| Full-600 per-item argmax | 0.486298 |

The full-pool argmax would set v6 to `0.995` and v22 to `0.98`; other cuts
stay unchanged.  Its relevant cell changes are v6 `2/17/2 → 1/1/3`
(TP/FP/FN) and v22 `2/1/0 → 2/0/0`.  Trusted net `(TP-FP)` does not fall for
any trusted item.

## Split-half decision

Halves are fixed before scoring by SHA-256(record ID) parity: 285/315 IDs.
Each half chooses on one side and scores the other.

| Train half | Test Macro, current | Test Macro, tuned | Result |
| --- | ---: | ---: | --- |
| 0 (285) | 0.418696 | 0.418696 | no gain |
| 1 (315) | 0.430809 | 0.430809 | no gain |

The adoption rule requires a gain in both directions.  It therefore fails;
`script.py` and the operational thresholds are deliberately unchanged.

Machine-readable result: ignored local artifact
`artifacts/offdev-600-1790471557297701344/threshold-measurement-r2/thresholds.json`.
