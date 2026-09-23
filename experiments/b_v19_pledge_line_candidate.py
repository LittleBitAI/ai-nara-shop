"""B v19 — 입찰 단계 시점을 확약서가 적힌 줄 안에서만 찾는다. 채택하지 않은 후보다.

운영 `v19_demanded_at_bid_stage()` 는 `확약서` 앞뒤 200자에서 입찰 단계 시점을 찾는다. dev 오탐 셋
(`096`·`098`·`112`)은 그 창이 옆 문장·옆 목록 항목의 마감 표현(중소기업확인서 발급 기한, 입찰참가
등록 기한)을 집어서 살아남았다. 이 후보는 창을 그 줄과 200자 창의 교집합으로 좁힌다 — 넓어지지 않는다.

무라벨에서 목록 머리말에 시점이 있는 정탐 꼴을 지운다(`가. 투찰 시 제출` 아래 `⑨ 확약서 1부`).
그래서 채택하지 않았다. 근거와 수치는 `reports/team-b/b8-v19-fp3/README.md`.

재생:
    python -X utf8 tools/replay_run.py --case reports/runs/colab-1789902969401579900/dev-debug \
      --candidate experiments/b_v19_pledge_line_candidate.py --output-dir <새 경로>
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def baseline():
    """재생기가 읽은 제출 코드를 집는다. 단독 import 면 저장소 루트의 것을 읽는다."""
    submitted = sys.modules.get("submission")
    if submitted is not None:
        return submitted
    import importlib.util
    spec = importlib.util.spec_from_file_location("baseline_script", ROOT / "script.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def demanded_in_pledge_line(rec: Dict[str, Any]) -> bool:
    base = baseline()
    for doc in rec.get("docs") or []:
        text = doc.get("text") or ""
        for found in base.V19_PLEDGE.finditer(text):
            start = max(text.rfind("\n", 0, found.start()) + 1, found.start() - base.V19_WINDOW)
            end = text.find("\n", found.end())
            end = min(end if end >= 0 else len(text), found.end() + base.V19_WINDOW)
            if base.V19_BID_DEADLINE.search(text[start:end]):
                return True
    return False


def postprocess(judgment: Dict[str, Dict[str, Any]], rec: Dict[str, Any]):
    base = baseline()
    original = base.v19_demanded_at_bid_stage
    base.v19_demanded_at_bid_stage = demanded_in_pledge_line
    try:
        return base.postprocess(judgment, rec)
    finally:
        base.v19_demanded_at_bid_stage = original
