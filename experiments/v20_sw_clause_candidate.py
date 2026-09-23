"""후처리 후보 — v20 을 모델이 아니라 공고의 두 결정적 신호로 판정한다.

모델 뒤 단계만 바꾼다. `tools/replay_run.py --candidate` 로 갈아 끼운다. GPU 를 쓰지 않는다.

v20 은 "입찰참가자격 (SW)" 부재탐지다. SW 사업인데 「소프트웨어 진흥법」 제48조의
대기업 참여제한 문구가 공고에 없으면 1 이다. 이 후보는 둘을 모두 공고에서 직접 읽는다.

- SW 사업: 소프트웨어사업자(컴퓨터관련서비스사업, 업종코드 1468) 등록을 참가자격으로 요구한다
  (`meta.면허업종제한목록` 또는 본문).
- 제48조 문구: 소프트웨어 진흥법 제48조 · 사업금액별 참여 제한 · 중소 소프트웨어사업자 등의 표현.

## 왜 모델을 버리나 — 오판 8건이 전부 공고를 잘못 읽은 것이다

H4(`colab-1789902969401579900`)와 A8 두 회차에서 v20 은 TP 1 / FP 4 / FN 4 로 같다.

| 공고 | 라벨→예측 | 원인 |
| --- | --- | --- |
| `24` `131` `134` | 1→0 | 모델은 SW·조항 없음으로 맞게 읽었다. 제안요청서 탈락이라 `software_complete` 가 보류 |
| `132` | 1→0 | 모델이 SW 사업이 아니라고 했다. meta 에 1468 제한이 있다 |
| `064` `068` | 0→1 | 공고문에 제48조 참여제한이 명시돼 있는데 모델 인용은 null. 200건 전부 null 이다 |
| `056` `144` | 0→1 | 1468 요구가 없는데 모델이 SW 사업이라 했다(`144` 는 자전거용타이어) |

법령 원문 주입(PR #82, A8)은 이 여덟 중 어느 것도 못 건드렸다 — 조문이 모자란 것이 아니다.

## 측정 (2026-09-23, 모델 미사용)

`18f07e5` 원응답(`colab-1789902969401579900/dev-debug`)을 HEAD 로 재생했다.

| | v20 TP/FP/FN | v20 F1 | Macro |
| --- | --- | ---: | ---: |
| HEAD 재생 | 1 / 4 / 4 | 0.200 | 0.618427228373 |
| 이 후보 | 5 / 2 / 0 | 0.833 | 0.644816117262 (+0.026389) |

바뀐 셀 10개, 전부 v20 이다. 대상 밖 0.

무라벨 카나리(`open/train_unlabeled.jsonl` 20,000건, `v20_decision`): 1 이 457건(2.29%),
dev 7/200(3.50%) — 배율 0.65. 모델 판정을 남기는 보류(None)는 255건(1.28%), dev 0건.

무라벨 2,000건에서 후보가 모델과 갈리는 층과 내리는 48셀의 사실 확인은
`reports/label-compare/unlabeled-v20/README.md` 가 소유한다. 채택 판결 2026-09-23.

## 알려진 약점

- 양성 5건을 보고 만든 규칙이다. dev 에서 FP 로 남는 `124`·`135` 는 둘 다
  "소기업·소상공인 제한"이지만 2건이라 규칙으로 올리지 않는다.
- 제안요청서가 탈락한 공고에서도 1 을 쓴다. 조항이 빠진 문서에 있었을 수 있다.
"""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path
from typing import Any, Dict, Optional

REPO = Path(__file__).resolve().parents[1]

JUDGMENT_DOCS = ("공고문", "제안요청서")
# Additions: only the 1468 (computer-related services) registration every dev positive had.
SW_PROVIDER = re.compile(r"소프트웨어\s*사업자[^\n]{0,40}?(?:컴퓨터\s*관련\s*서비스|1468)")
# Removals: any software-provider registration at all (1426, 1469, 1470, uncoded "등록 업체", ...).
# A notice matching this but not SW_PROVIDER keeps the model's answer.
ANY_SW_PROVIDER = re.compile(r"소프트웨어\s*(?:산업\s*)?사업자\s*(?:[(\[（]|(?:로\s*)?(?:등록|신고)|등록증)")
# `제48조` 만으로는 안 된다 — 국가·지방 계약법 시행령·시행규칙 제48조(동가 입찰·개찰)가 dev 에 13건 있다.
# The restriction itself: 제48조, its pre-renumbering 제24조의2, the 하한 고시 title, or the amount-band wording.
SW_CLAUSE = re.compile(
    r"소프트웨어\s*(?:산업\s*)?진흥법[」』\s]*제\s?48조"
    r"|소프트웨어\s*산업\s*진흥법[」』\s]*제\s?24조의\s?2"
    r"|제48조\s*\(중소\s*소프트웨어"
    r"|대기업인?\s*소프트웨어\s*사업자가?\s*참여\s*할\s*수\s*있는\s*사\s*업\s*금\s*액"
    r"|사업금액별\s*참여"
    r"|입찰참여\s*제한금액")
# A bare name is not the restriction (PPS-D-004071 cites 시행령 제41조 "중소 소프트웨어사업자의 기준" as a
# qualification). 61 of 20,000 unlabeled match only this way, dev 0 — the model keeps its answer.
SW_HINT = re.compile(r"대기업인?\s*소프트웨어|중소\s*소프트웨어\s*사업자")


def _load_script():
    spec = importlib.util.spec_from_file_location("baseline_script", REPO / "script.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_SCRIPT = None


def baseline():
    global _SCRIPT
    if _SCRIPT is None:
        _SCRIPT = sys.modules.get("run_submission") or sys.modules.get("submission") or _load_script()
    return _SCRIPT


def sw_participation_missing(rec: Dict[str, Any]) -> Optional[bool]:
    """SW 사업이면 제48조 문구가 없는지를, SW 사업이 아니면 None 을 돌려준다."""
    texts = [doc.get("text") or "" for doc in rec.get("docs") or []]
    meta = rec.get("meta") or {}
    if "1468" not in (meta.get("면허업종제한목록") or "") and not any(SW_PROVIDER.search(t) for t in texts):
        return None
    return not any(SW_CLAUSE.search(t) for t in texts)


def v20_decision(rec: Dict[str, Any]) -> Optional[int]:
    """1 or 0 when the notice's text settles v20, None to keep the model's answer.

    Removal (0) needs a text fact: no software-provider registration of any kind, or the
    제48조 sentence is present. A notice registering some other software category without
    the sentence is left to the model — calling it either way would be a legal judgment.
    """
    docs = rec.get("docs") or []
    texts = [doc.get("text") or "" for doc in docs]
    # 지침 제3조② puts the statement in 공고문 or 제안요청서 (script.py `software_docs`).
    # Only there does the sentence settle v20. Elsewhere (과업지시서, 규격서) dev has no case
    # either way — 40 of 20,000 unlabeled — so the model keeps its answer.
    if any(SW_CLAUSE.search(doc.get("text") or "") for doc in docs if doc.get("type") in JUDGMENT_DOCS):
        return 0
    if any(SW_CLAUSE.search(t) or SW_HINT.search(t) for t in texts):
        return None
    if sw_participation_missing(rec):
        return 1
    licenses = (rec.get("meta") or {}).get("면허업종제한목록") or ""
    if "소프트웨어사업자" in licenses or any(ANY_SW_PROVIDER.search(t) for t in texts):
        return None
    return 0


def postprocess(judgment: Dict[str, Dict[str, Any]], rec: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    out = baseline().postprocess(judgment, rec)
    decision = v20_decision(rec)
    if decision is not None:
        # 부재탐지 항목이라 근거는 늘 빈칸이다(script.py 의 ABSENCE).
        out["v20"] = {"위반여부": decision, "근거문구": ""}
    return out
