# Off-dev 600 logprob threshold measurement — 2026-09-27

Status after the PR #163 hold review (round 1): the numbers below were measured with code that
the review found wrong, so they are withdrawn. The tool is fixed; the measurement has not been
rerun, because the 600 archive (`artifacts/offdev-600-1790471557297701344/`, Drive
`MyDrive/a5/offdev-600-deb6831ff0e2/`) is not in the repository. No verdict on the candidate yet.

| Review finding | Fix |
| --- | --- |
| P1 `to_csv_bytes()` wrote CRLF; `script.write_csv()` writes LF | LF restored. The byte match below was against a CRLF combined CSV, so the mismatch lives in how that combined file was assembled, not in the replay |
| P1 split used unsalted SHA-256, not the fixed `half(id)` | The tool imports `half` from `reports/labels-3000/pick.py` (298/302 on the 600, per the review) |
| P2 only the five items already in `ITEM_THRESHOLDS` were searched | Every labelled item except v9/v24 is searched, with a no-cut (argmax) option |
| P2 Macro averaged 24 items, two of them unlabelled | Macro is over the labelled items (22) |

Rerun, once the archive is back:

```
python -X utf8 tools/tune_offdev_thresholds.py --case <combined 600 case dir> \
  --input <600 records in manifest order> --truth <diag + sealed labels> --out <new dir>
```

Smoke check of the fixed tool on dev (`colab-1790432295199698396/dev-debug`, dev labels):
22 items searched, grid starts with no-cut, halves A/B 106/94 — dev picks the current cuts, as expected.

## Withdrawn round-0 record

### Reproducibility gate

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

### Measurement

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

### Split-half decision

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
