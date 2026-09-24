"""B10 candidate — a v21 positive stands only on a quoted share below the statutory floor.

Post-model step only. Swap it in with `tools/replay_run.py --candidate`. No GPU.
v21 is "공동 5% (10%)": a per-member minimum share set below the floor (local 5%, national
joint-performance 10%, `script.v21_minimum_share()`). The operating rule already drops quotes
whose shares all meet the floor, and quotes that bar joint contracting outright
(`V21_JOINT_BARRED`). That second regex misses the commonest wording ("허용되지 않습니다",
"미허용", "참여할 수 없습니다"), and the unlabeled run shows the cost: all 84 v21 positives
in 6,000 notices quote no share at all, while every dev true positive quotes one.

The candidate drops a v21 positive whose verified quote holds no percentage. It only lowers.
Adoption is decided on the unlabeled deletion set by `q < F/2`, not on dev
(reports/team-b/b10-v21-quote-share/README.md).

Replay:
    python -X utf8 tools/replay_run.py --case reports/runs/colab-1789902969401579900/dev-debug \\
      --candidate experiments/b10_v21_quote_share_candidate.py --output-dir <new dir>
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def baseline():
    """The submission code the replayer loaded; the repository's script.py when imported alone."""
    submitted = sys.modules.get("submission")
    if submitted is not None:
        return submitted
    import importlib.util
    spec = importlib.util.spec_from_file_location("baseline_script", ROOT / "script.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def quotes_no_share(evidence: str) -> bool:
    return not baseline().V21_PERCENT.search(evidence or "")


def postprocess(judgment: Dict[str, Dict[str, Any]], rec: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    out = baseline().postprocess(judgment, rec)
    if out["v21"]["위반여부"] == 1 and quotes_no_share(out["v21"]["근거문구"]):
        out["v21"] = {"위반여부": 0, "근거문구": ""}
    return out
