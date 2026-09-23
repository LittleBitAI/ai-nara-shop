"""B v24 — 등록 플래그가 `N` 인 축은 불일치로 세지 않는다.

`region_diff`·`industry_diff` 는 두 방향을 불일치로 센다. (1) 등록이 제한인데 걸린 지역·업종
집합이 본문과 다르다. (2) 본문이 지역·업종을 거는데 등록 플래그(`지역제한여부`·`업종제한여부`)가
`N` 이다. 이 후보는 (2)만 끈다. (1)·제목 태그 축·모델 인용 검사는 그대로다.

근거는 조문이 아니다 — v24 는 조문 없는 대조형이고, 운영진은 (2)의 방향을 묻자 답하지 않았다
("각 공고를 정의대로 비교하라", `docs/qna.md` v24 절 S7-14). 이 후보가 기대는 것은 dev 라벨이다.
모델 출력과 무관하게 dev 200건 전체에서 (2)가 서는 공고의 v24 정답은 지역 1/12 · 업종 0/6 이다
(`reports/team-b/b7-v24-fp12/README.md`). dev 에서 온 규칙이므로 무라벨 발화율을 함께 본다(W5).

모델을 부르지 않는다. 추가 호출 0 · 추가 시간 0초.

재생:
    python -X utf8 tools/replay_run.py --case reports/runs/colab-1789902969401579900/dev-debug \
      --candidate experiments/b_v24_flag_direction_candidate.py --output-dir <새 경로>
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# 축 이름 → 그 축의 등록 플래그. 플래그가 `Y` 가 아니면 그 축은 불일치를 내지 않는다.
FLAG = {"지역제한": "지역제한여부", "업종": "업종제한여부"}


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


def _flagged(name, axis):
    flag = FLAG.get(name)
    if flag is None:
        return axis

    def gated(rec, body, meta):
        return axis(rec, body, meta) if meta.get(flag) == "Y" else None
    return gated


def postprocess(judgment: Dict[str, Dict[str, Any]], rec: Dict[str, Any]):
    base = baseline()
    original = base.AXES
    base.AXES = tuple((name, _flagged(name, axis)) for name, axis in original)
    try:
        return base.postprocess(judgment, rec)
    finally:
        base.AXES = original
