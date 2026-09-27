"""Pick the labels-3000 notices and fix the split-half partition, before any label is read.

The pool is the unlabeled D run chunks u00~u10 (saved model responses; u11 cannot be replayed), minus the
diagnostic 200, the sealed 400 and every notice an earlier labeler saw (the list `pick_diag.py` uses).
A seeded shuffle of the sorted pool gives the order; the first 3,000 are the sample and the first 100 of
those are the pilot, so a smaller run is still a prefix of one random order.

`half(id)` is the split-half partition for the whole off-dev pool (diagnostic 200, sealed 400, labels-3000):
a hash of the notice ID with a fixed salt, so it does not depend on which set a notice is in.

  python -X utf8 reports/labels-3000/pick.py
"""

import hashlib
import json
import random
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).parent
sys.path.insert(0, str(ROOT / "reports" / "labels-600"))
from pick_diag import LABELED  # noqa: E402

SEED = 20260927
SIZE, PILOT = 3000, 100
SALT = "labels-3000-half"
CHUNKS = [f"u{i:02d}" for i in range(11)]


def half(identifier: str) -> str:
    return "A" if hashlib.sha256(f"{SALT}:{identifier}".encode()).digest()[0] % 2 == 0 else "B"


def main():
    runs = ROOT / "reports" / "label-compare" / "unlabeled-d"
    pool = set()
    for chunk in CHUNKS:
        (ids_path,) = runs.glob(f"run-*/{chunk}/ids.json")
        ids = json.loads(ids_path.read_text(encoding="utf-8"))
        pool |= set(ids if isinstance(ids, list) else ids["ids"])
    excluded = set()
    for name in LABELED:
        excluded |= set(re.findall(r"PPS-D-\d+", (ROOT / name).read_text(encoding="utf-8")))
    for name in ("diag-ids.txt", "sealed-ids.txt"):
        excluded |= set((ROOT / "reports" / "labels-600" / name).read_text(encoding="utf-8").split())
    eligible = sorted(pool - excluded)
    order = eligible[:]
    random.Random(SEED).shuffle(order)
    picked = order[:SIZE]
    out = HERE / "ids.txt"
    out.write_text("\n".join(picked) + "\n", encoding="utf-8", newline="\n")
    manifest = {
        "seed": SEED, "size": SIZE, "pilot": PILOT, "chunks": CHUNKS,
        "pool": len(pool), "excluded_in_pool": len(pool & excluded), "eligible": len(eligible),
        "excluded_sources": LABELED + ["reports/labels-600/diag-ids.txt", "reports/labels-600/sealed-ids.txt"],
        "half_salt": SALT, "half_A_in_sample": sum(half(i) == "A" for i in picked),
        "ids_sha256": hashlib.sha256(out.read_bytes()).hexdigest(),
    }
    out.with_suffix(".manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({k: v for k, v in manifest.items() if k != "excluded_sources"}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    assert half("PPS-D-000001") in "AB"
    sys.exit(main())
