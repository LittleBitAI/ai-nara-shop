"""C6 후보 E — v16 은 자격 문장의 **역할을 못 정한** 공고에서 올리지 않는다.

**이 후보는 dev 라벨 기반이다.** 방침이 다시 바뀔 때 무엇을 되돌릴지 알아야 하므로
먼저 적는다 — 판별축 `qualification_role == "none"` 을 항목 정의나 조문으로 정당화할 수
없다. dev 의 v16 오탐을 보고 고른 축이고, 표본은 **2건**이다.

dev 에서 결정표가 `decided` 로 v16 을 만진 8건을 역할별로 폈다.

| `qualification_role` | TP | FP |
| --- | ---: | ---: |
| `checklist` | 4 (037·058·067·20) | 1 (089) |
| `none` | 0 | **2** (111·149) |

`none` 은 "자격 제한으로 읽을 문장을 어떤 역할로도 분류하지 못했다"는 상태다. v16 은
부재탐지(1억원 이상 일반물품에서 소기업 제한이 **없음**)이므로, 역할을 못 정했다는 것과
제한이 없다는 것을 같게 취급하면 **관측 실패를 위반으로 바꾼다.** 운영 코드는 지금
`role in ("checklist", "legal_reference", "none")` 에서 `unrestricted` 를 허용한다.

**v16 에만 좁힌다.** 같은 축을 v18 에 쓰면 안 된다 — v18 의 `role=none` 은 dev 에서
TP 2(040·041) · FP 2(061·097) 로 **갈리지 않고**, 닫으면 TP 를 지운다. 그것은 방침과
무관한 금지선이다.

모델을 부르지 않는다. 추가 호출 0 · 추가 시간 0초.

재생:
    python -X utf8 tools/replay_run.py \
      --case reports/runs/colab-1790235508743452453/dev-debug \
      --script <기준 커밋의 script.py> \
      --candidate experiments/c6_v16_role_none_candidate.py --output-dir <새 경로>
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

ITEM = "v16"
UNDECIDED_ROLE = "none"


def baseline():
    """재생기가 읽은 제출 코드를 집는다. 단독 import 면 저장소 루트의 것을 읽는다."""
    submitted = sys.modules.get("submission")
    if submitted is not None:
        return submitted
    spec = importlib.util.spec_from_file_location("baseline_script", ROOT / "script.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def verify_company_size(facts: dict[str, Any], rec: dict[str, Any], max_chars: int):
    """운영 판정을 낸 뒤, 역할 미정 공고의 v16 만 0 으로 되돌린다.

    **결정표가 이번에 올린 셀만** 되돌린다. 앞 단계(baseline·SME)가 남긴 양성은
    이 후보의 대상이 아니다 — 그것은 다른 경로의 판단이고 여기서 가로채지 않는다.
    """
    script = baseline()
    out, reason = script.verify_company_size(facts, rec, max_chars)
    if (facts.get("qualification_role") == UNDECIDED_ROLE
            and (out.get(ITEM) or {}).get("위반여부") == 1):
        out = dict(out)
        out[ITEM] = {"위반여부": 0, "근거문구": None}
    return out, reason
