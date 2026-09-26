"""C11 — 공고가 「판로지원법 시행령」 제7조제1항의 예외를 적용했다고 적으면 중기간 경쟁제품
항목이 서지 않는다.

v10·v11·v12·v13 은 전부 **중소기업자간 경쟁입찰**을 전제로 하는 항목이다
(`docs/items.md` — "중기간 경쟁제품 …"). 그 입찰이 아니면 항목이 애초에 안 선다.

## 조문이 이 축을 만든다 — 공고 문구를 주운 것이 아니다

제공 스냅샷 `중소기업제품 구매촉진 및 판로지원에 관한 법률 시행령` 제7조가 적는다.

> **제7조(중소기업자간 경쟁입찰의 예외 등)**
>   ① 법 제7조제1항에서 "대통령령으로 정하는 특별한 사유"란 다음 각 호의 어느 하나에
>      해당하는 경우를 말한다.
>     …
>     4. 특정한 기술·용역이 필요한 경우 등 공공기관의 특별한 사정으로 인하여
>        **중소기업자간 경쟁입찰 외의 방법으로 구매**하려는 경우
>   ② 공공기관의 장은 제1항 각 호의 어느 하나에 해당하여 중소기업자간 경쟁입찰 외의
>      방법으로 조달계약을 체결하려는 경우 **그 사유를 입찰공고문에 기재**하거나 …

**제2항이 이 규칙의 근거다.** 예외를 쓰려면 공고문에 적어야 하므로, 공고문에 그 인용이
있다는 것은 발주처가 스스로 "이 입찰은 중기간 경쟁입찰이 아니다"라고 밝힌 것이다.
특정 공고의 표현을 정규식에 박는 것이 아니라 **법이 요구한 기재 사항**을 읽는다.

## 왜 품번 축(C9)으로는 못 잡나

`PPS-DEV-23` 의 세부품명번호 `2513189901` 은 제공 고시에 **있다**(드론 · 특수항공기).
품목은 경쟁제품이 맞다. 그런데 발주처가 제7조제1항제4호를 적용해 경쟁입찰에서 뺐다.
`c9_catalogue_exclusion_candidate` 의 고시 대조 축은 이 공고를 `True`(경쟁제품)로 읽으므로
**닿지 않는다.** 두 후보는 서로 다른 것을 본다.

## 발화

| | 발화 | 발화율 |
| --- | ---: | ---: |
| dev 200건 | 1 (`PPS-DEV-23`) | 0.00500 |
| 무라벨 20,000건 | 19 | 0.00095 |

무라벨 19건의 문맥이 **전부 같은 뜻**이다 — "중소기업자간 경쟁입찰의 예외에 해당합니다",
"중소기업자간 경쟁입찰에 대한 예외를 적용", "비영리법인, 대기업도 참여가 가능합니다".
문구 축(`제외` 계열 정규식)이 무라벨에서 세 가지 다른 뜻을 주워 기각된 것과 대조된다.

법률명을 앵커로 묶는다. 그러지 않으면 `PPS-DEV-103` 의 「공공디자인의 진흥에 관한 법률」
시행령 제7조제1항이 걸린다 — 딴 법의 같은 조 번호다.

## `main` 위에서도 같은 값이다 (2026-09-27)

PR #156 이 C7·C9 를 `script.py` 에 이식한 뒤 `origin/main`(`3a7eeec`) 을 기준선으로
같은 여섯 통과에 재생했다. **여섯 통과 전부 한 셀(`PPS-DEV-23` v10) · +0.001587301587**
로 `772ca12` 기준일 때와 같다. 이식된 규칙들과 겹치지 않는다.

**C11 은 `main` 에 안 들어간 유일한 C 후보다.** 자세한 수는
`reports/team-c/v10-v11-v13-breakdown/README.md` §10 이 소유한다.

모델을 부르지 않는다. 제공 법령 스냅샷과 공고 원문만 쓴다. 추가 호출 0 · 추가 시간 0초.

재생:
    python -X utf8 tools/replay_run.py \
      --case reports/runs/colab-1790445336782946136/var-01 \
      --script <기준 커밋의 script.py> \
      --candidate experiments/c11_competition_exception_candidate.py --output-dir <새 경로>
"""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# 중기간 경쟁입찰을 전제로 하는 항목. 그 입찰이 아니면 넷 다 안 선다.
ITEMS = ("v10", "v11", "v12", "v13")
# 「중소기업제품 구매촉진 및 판로지원에 관한 법률 시행령」 제7조제1항. 줄여 쓴 「판로지원법
# 시행령」도 받는다. 법률명과 조 번호 사이를 좁게 잡아 다른 법의 제7조가 안 끼게 한다.
EXCEPTION = re.compile(r"(중소기업제품\s*구매촉진|판로지원)[^\n]{0,40}?시행령[^\n]{0,15}?"
                       r"제\s*7\s*조\s*제\s*1\s*항")


def baseline():
    """재생기가 읽은 제출 코드를 집는다. 단독 import 면 저장소 루트의 것을 읽는다."""
    submitted = sys.modules.get("submission")
    if submitted is not None:
        return submitted
    spec = importlib.util.spec_from_file_location("baseline_script", ROOT / "script.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def competition_exception(rec: dict[str, Any]) -> bool:
    """공고가 시행령 제7조제1항의 예외를 적용했다고 적는가.

    문서 전문을 본다. 제2항이 요구하는 기재는 공고문 어디에나 올 수 있고, 프롬프트
    예산(16,000자)에 잘린 뒤쪽에 있을 수도 있다. 이 규칙은 모델이 본 것이 아니라
    **제공된 입력**을 읽는다.
    """
    return any(EXCEPTION.search(doc.get("text") or "") for doc in (rec.get("docs") or []))


def postprocess(parsed: dict[str, Any], rec: dict[str, Any]):
    """운영 후처리를 낸 뒤, 예외 공고의 네 항목만 0 으로 닫는다.

    닫기만 한다. 0 을 1 로 만들지 않는다. 근거문구는 비운다.
    """
    script = baseline()
    out = script.postprocess(parsed, rec)
    if not competition_exception(rec):
        return out
    for item in ITEMS:
        cell = out.get(item)
        if cell and cell.get("위반여부") == 1:
            out[item] = {"위반여부": 0, "근거문구": None}
    return out
