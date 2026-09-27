# Evidence-first main schema — how the GPU run is judged (fixed 2026-09-27 21:00, before results)

Code `d45576f16beb33b0dc4afb7da489ca0d3fd18fdf`: branch `exp/0927-best` (`be87c9f`) plus `EVIDENCE_FIRST`, which makes
the main call write `근거문구` before `위반여부` for every item. Runs: `notebooks/colab-ef-600.ipynb` (off-dev 600) and
`notebooks/colab-ef-dev.ipynb` (dev 200).

1. Both runs complete; each replays its own CSV byte for byte.
2. Baseline: `be87c9f` replayed on the facts-call 600 run (`c23ed84`) and dev run (`278ca53`), as measured tonight:
   off-dev 600 0.570612 (half A 0.485084, half B 0.500073), dev 0.825466.
3. The evidence-first run's own CSVs are scored the same way (diagnostic + sealed labels, 수의계약 left out, `half(id)`).
4. Adopted for the 9/27 upload when off-dev 600 Macro is higher, both halves are higher, and dev drops by no more than 0.01.
   The two sides are different GPU runs; the same code varies by up to 0.007 between passes (#152), so a gain smaller
   than that is reported but does not decide on its own: then `be87c9f` is uploaded.
5. The logprob cuts were fitted to verdict-first outputs. The run is also scored with no cuts (`ITEM_THRESHOLDS = {}`),
   reported next to it; the adopted version is whichever of the two passes 4, the higher if both do.
6. Server time: the run's inference seconds per notice against `be87c9f`'s; over 6,800 s estimated means not adopted.
7. Not scored by 23:10 → `be87c9f` is uploaded.

## Combined run (added 21:05, before any result)

Code `8a274ec82dfb12c7154bdd4154801a4bec810995` adds, on top of the evidence-first code, a `조항역할` field between quote and
verdict, a prompt rule with contrastive examples (positives from dev gold; negatives generic, none from the off-dev 600),
and a postprocess gate that zeroes v1–v8 on evaluation, checklist or law-citation quotes. Runs:
`notebooks/colab-efplus-600.ipynb`, `notebooks/colab-efplus-dev.ipynb`. Judged exactly as above, against the same
`be87c9f` baseline; also replayed with the role gate off. Dev is inflated on v1–v3 by the dev-gold examples, so the
dev check (drop ≤ 0.01) is the only use of dev here. If both the evidence-first run and the combined run pass, the one
with the higher off-dev 600 Macro goes up.
