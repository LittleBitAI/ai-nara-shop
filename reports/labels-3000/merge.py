"""Merge the labels-3000 passes into one label CSV with the labels-600 rules and trust verdicts.

Same four passes and prompts as labels-600 (24-item `34bd9cf7`, facts `43380d80`, focus `740bf1c4`,
v1 `25f869e7` three runs), so `merge_labels.sources()` applies unchanged. Only notices the 24-item pass
labelled are written; a notice missing from another pass fails loudly rather than being filled.

  python -X utf8 reports/labels-3000/merge.py
"""

import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent / "labels-600"))
import merge_labels  # noqa: E402


def main():
    ids = (HERE / "ids.txt").read_text(encoding="utf-8").split()
    merge_labels.merge(HERE / "merged.csv", merge_labels.load_records(ids), merge_labels.sources(),
                       HERE / "wide", HERE / "facts", HERE / "focus",
                       [HERE / "v1" / f"run{n}" for n in (1, 2, 3)])
    return 0


if __name__ == "__main__":
    sys.exit(main())
