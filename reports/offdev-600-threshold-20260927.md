# Off-dev 600 logprob threshold measurement — 2026-09-27

Status after the PR #163 hold review (rounds 1–3): the withdrawn round-0 numbers remain invalid.
The supplied `offdev-600-results-1790471557297701344.zip` archive was then recovered locally and
remeasured with the reviewed tool and the archived `deb6831` submission code.  The candidate fails
the fixed split-half gate; operational thresholds remain unchanged.

| Review finding | Fix |
| --- | --- |
| P1 `to_csv_bytes()` wrote CRLF; `script.write_csv()` writes LF | LF restored. The byte match below was against a CRLF combined CSV, so the mismatch lives in how that combined file was assembled, not in the replay |
| P1 split used unsalted SHA-256, not the fixed `half(id)` | The tool imports `half` from `reports/labels-3000/pick.py` (298/302 on the 600, per the review) |
| P2 only the five items already in `ITEM_THRESHOLDS` were searched | Every labelled item except v9/v24 is searched, with a no-cut (argmax) option |
| P2 Macro averaged 24 items, two of them unlabelled | Macro is over the labelled items (22) |
| Round 2 P1: split-half pass judged cuts picked per half, not the full-pool cut that is reported | A full-pool cut is picked only if it beats the baseline item F1 on half A and on half B; `split_half_pass` also requires the final candidate's Macro to rise on each half (`final_by_half`) |
| Round 2 P1: `item_p1` completeness checked by map count only | Every searched item needs `item_p1` on every notice, or the tool stops |

Rerun, once the archive is back:

```
python -X utf8 tools/tune_offdev_thresholds.py --case <combined 600 case dir> \
  --input <600 records in manifest order> --truth <diag + sealed labels> \
  --script <archived deb6831 script.py> --out <new dir>
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

## Verified rerun from the supplied Colab archive

The archive's original shards, not a GPU rerun, were used.  `u00` (500 rows) and `u01` (100 rows)
each reproduce their own archived LF CSV byte-for-byte when replayed with the source commit
`deb6831ff0e2c008c9479ad80013a701b5ffdb1` recovered from the shared Git object database.

| shard | rows | CSV SHA-256 | result |
| --- | ---: | --- | --- |
| u00 | 500 | `1da908a47474d231cdb3a1d5a5294f0e0a8f77b7872489d5571ba7f5097b7640` | identical |
| u01 | 100 | `535267fb806d631f22ad7968fdad397d6c707c69bf06125911da02776961e8f1` | identical |

The reviewed tuner searches all 22 labelled items (v9/v24 fixed), includes no-cut, requires every
searched `item_p1`, and uses the fixed salted `half(id)` partition: A=298, B=302.

| measurement | Macro F1 (22 labelled items) |
| --- | ---: |
| current archived thresholds | 0.514170 |
| full-pool candidate | 0.525625 |

The full-pool candidate would add v3=`0.95` and raise v6 to `0.7`.  It passes the trusted net
`TP-FP` guard, but fails the adoption rule: a cut chosen on A scores B `0.464069 -> 0.460106`
(down), while a cut chosen on B scores A `0.449220 -> 0.454638` (up).  Therefore
`split_half_pass=false`; no `script.py` threshold change is permitted.

## Current-code replay gate

The prior section is explicitly an **archived-code measurement**: it passes
`--script artifacts/.../script-deb6831.py`, because those were the exact GPU
responses' post-processing semantics.  It cannot decide the current main
post-processing gate on its own.

The same 600 saved responses were therefore replayed with the current PR
`script.py` (no `--script` override), using the same reviewed 22-item grid,
fixed salted A/B split, and `item_p1` completeness guard.

| measurement | Macro F1 |
| --- | ---: |
| current script baseline | 0.499681 |
| current script full-pool candidate | 0.508940 |

The final current-code candidate adds only v3=`0.95`; its configured cuts are
otherwise unchanged.  Its final candidate improves both fixed halves
(A `0.446440 -> 0.460293`, B `0.431193 -> 0.434223`), and the independently
chosen cross-half candidates also improve both held-out sides.  Thus
`split_half_pass=true` and `trusted_guard_pass=true` for current code.

This is still **not an operational threshold adoption**: the fixed adoption
rule also requires a matching dev replay with Macro drop no greater than
0.01.  That dev gate has not yet been run, so `script.py` remains unchanged.
