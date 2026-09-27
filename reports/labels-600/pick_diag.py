"""Pick the 200 diagnostic notices from the unlabeled GPU run (6,000 notices, raw responses kept).

150 notices where the current code fires at least one weak item, 50 from the rest, seed 20260926.
Notices any earlier labeler already saw are excluded. This set is not random; its F1 is not a
server proxy. Replay the chunks with the current code first (u11 cannot be replayed):

  python -X utf8 tools/replay_run.py --case reports/label-compare/unlabeled-d/<run>/uNN/output \
      --input <that chunk's records> --output-dir <replay>/replay-uNN
  python -X utf8 reports/labels-600/pick_diag.py <replay>
"""

import csv
import hashlib
import json
import random
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).parent
WEAK = ["v2", "v9", "v10", "v11", "v13", "v16", "v18", "v24"]
SEED = 20260926
FIRED, REST = 150, 50
# Files that hold labels from an earlier labeler. GPU-run outputs are not labels and stay eligible.
LABELED = [
    "reports/label-compare/opus5-unlabeled40.jsonl",
    "reports/label-compare/unlabeled-d/labels-opus55.jsonl",
    "reports/label-compare/unlabeled-v20/facts-w48.jsonl",
    "reports/label-compare/unlabeled-v20/layers.jsonl",
    "reports/team-b/b10-v21-quote-share/b10-facts-unlabeled.jsonl",
    "reports/team-b/b12-v19-expand/line-deletion-43.jsonl",
    "reports/team-b/b12-v19-expand/unlabeled-300.jsonl",
]


def main(replay_root):
    labeled = set()
    for name in LABELED:
        labeled |= set(re.findall(r"PPS-D-\d+", (ROOT / name).read_text(encoding="utf-8")))
    sealed = set((HERE / "sealed-ids.txt").read_text(encoding="utf-8").split())
    fired, rest, sources = [], [], {}
    for path in sorted(Path(replay_root).glob("replay-u*/submission.csv")):
        sources[path.parent.name] = hashlib.sha256(path.read_bytes()).hexdigest()
        with path.open(encoding="utf-8", newline="") as stream:
            for row in csv.DictReader(stream):
                if row["id"] in labeled:
                    continue
                (fired if any(row[item] == "1" for item in WEAK) else rest).append(row["id"])
    assert not sealed & set(fired + rest), "diagnostic pool overlaps the sealed set"
    rng = random.Random(SEED)
    picked = rng.sample(sorted(fired), FIRED) + rng.sample(sorted(rest), REST)
    out = HERE / "diag-ids.txt"
    out.write_text("\n".join(picked) + "\n", encoding="utf-8", newline="\n")
    manifest = {
        "seed": SEED, "weak_items": WEAK, "fired_pool": len(fired), "rest_pool": len(rest),
        "picked_fired": FIRED, "picked_rest": REST, "excluded_labeled": len(labeled),
        "script_sha256": hashlib.sha256((ROOT / "script.py").read_bytes()).hexdigest(),
        "replay_csv_sha256": sources,
        "ids_sha256": hashlib.sha256(out.read_bytes()).hexdigest(),
    }
    out.with_suffix(".manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({k: v for k, v in manifest.items() if k != "replay_csv_sha256"}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
