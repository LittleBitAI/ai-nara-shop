"""B v19 — bid-stage timing from the pledge's own line or from the heading of its list.

The line-scope candidate (#112) dropped dev FPs whose ±200-char window caught a neighbour's
deadline, but also dropped list entries whose timing lives in the list heading
(`가. 투찰 시 제출` above `⑨ 확약서 1부`). #112 wrote the next hypothesis: the unit is the
pledge's line plus the heading of the list it sits in, found where the line-marker kind changes.
Bid-stage expressions stay the operating `V19_BID_DEADLINE` (docs/tasks/b-facts-labeler.md).

    python -X utf8 tools/replay_run.py --case reports/runs/colab-1789902969401579900/dev-debug \\
      --candidate experiments/b_v19_heading_candidate.py --output-dir <new dir>
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any, Dict, Optional

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments"))
import b_v19_pledge_line_candidate as line  # noqa: E402

# Line markers by kind. Extracted text loses indentation, so the marker kind is the only depth cue.
MARKERS = (
    ("circled", r"[①-⑳]"),
    ("hangul", r"[가-하]\s*[.)]"),
    ("paren_num", r"\(?\d{1,2}\)"),
    ("num", r"\d{1,2}\s*\."),
    ("bullet", r"[-·•○◦❍□■▪※*]"),
)
MARKER = re.compile(r"^\s*(?:" + "|".join(f"(?P<{name}>{p})" for name, p in MARKERS) + r")")
HEADING_REACH = 40          # lines to walk up before giving up


def marker_kind(line_text: str) -> Optional[str]:
    found = MARKER.match(line_text)
    return found.lastgroup if found else None


def heading_of(lines, index) -> Optional[str]:
    """The first line above whose marker kind differs from this list entry's. None if not a list entry."""
    kind = marker_kind(lines[index])
    if kind is None:
        return None
    for up in range(index - 1, max(-1, index - 1 - HEADING_REACH), -1):
        text = lines[up]
        if not text.strip():
            continue
        other = marker_kind(text)
        if other != kind:
            return text
    return None


def demanded(rec: Dict[str, Any]) -> bool:
    base = line.baseline()
    if line.demanded_in_pledge_line(rec):
        return True
    for doc in rec.get("docs") or []:
        lines = (doc.get("text") or "").split("\n")
        for index, text in enumerate(lines):
            if base.V19_PLEDGE.search(text):
                heading = heading_of(lines, index)
                if heading and base.V19_BID_DEADLINE.search(heading):
                    return True
    return False


def postprocess(judgment: Dict[str, Dict[str, Any]], rec: Dict[str, Any]):
    base = line.baseline()
    original = base.v19_demanded_at_bid_stage
    base.v19_demanded_at_bid_stage = demanded
    try:
        return base.postprocess(judgment, rec)
    finally:
        base.v19_demanded_at_bid_stage = original
