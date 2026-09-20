"""후처리 후보 — v24 를 공고 제목의 금액구간 태그로만 판정한다.

모델 뒤 단계만 바꾼다. `tools/replay_run.py --candidate` 로 갈아 끼운다. GPU 를 쓰지 않는다.

v24 는 "공고서와 나라장터 입력값 상이"이고 연결할 조문이 없다. 원본 비고가
**예산·계약방법·지역제한·업종** 넷을 든다. 그중 코드가 결정적으로 대조할 수 있는 축을
dev 200건에서 찾아본 결과는 이렇다.

| 축 | 발화 | 정답 양성 | 오탐 |
| --- | ---: | ---: | ---: |
| **제목 태그의 계약방법·금액구간 ↔ meta** | 2 | **2** | **0** |
| 공고문 지역제한 표현 ↔ `meta.지역제한여부` | 11 | 1 | 10 |
| `meta.지역제한여부=Y` 인데 표현 없음 | 5 | 0 | 5 |
| `meta.업종제한여부=Y` 인데 목록 빔 | 0 | 0 | 0 |

**제목 태그 축만 정밀도가 있다.** 나머지 둘은 버린다 — 공고가 지역을 말하는 방식이
너무 다양해서 표현의 유무로는 등록값과의 불일치를 못 가른다.

제목 태그는 조문이 아니라 산술이다. 「(일반경쟁·1억원미만)」이라 써 놓고
`meta.입찰추정가격` 이 2.7억이면 어느 집합에서도 불일치다. 그래서 dev 표현에
맞춘 규칙이라기보다 대조 자체이고, 무라벨 발화율로 그것을 확인한다.

**이 후보는 v24 에서 모델 판정을 버린다.** 모델은 TP 4 / FP 32 / FN 4 (F1 0.182) 인데
오탐 32건 중 23건이 근거가 빈칸이다 — 무엇과 무엇을 대조했는지 말하지 못한 양성이다.
코드 규칙은 TP 를 둘 잃지만 오탐을 전부 없앤다.

## 반려 — 무라벨이 반대한다

**쓰지 마라.** dev 재생에서 Macro +0.009091(대상 밖 0)이 나왔지만
`open/train_unlabeled.jsonl` 6,000 건에서 **이 규칙의 발화가 0 건이다.**
제목 꼬리표 자체는 3,419 건(56.98%)에 있는데 등록값과 어긋난 것이 하나도 없다.
dev 에서는 200 건 중 2 건(1.00%)이다 — 전이 배율 **0.00**.

| | dev 200 | 무라벨 6,000 |
| --- | ---: | ---: |
| 제목 꼬리표 등장 | 47.00% | 56.98% (1.21배) |
| 등록값과 불일치 | 1.00% | **0.00% (0.00배)** |

비공개 1,853 건에서도 0 건이면 이렇게 된다.

| | dev | 서버 기대 |
| --- | --- | --- |
| **대체** (이 파일) | F1 0.182 → 0.400, Macro **+0.0091** | TP 둘을 버리고 아무것도 못 얻는다 — **방향이 뒤집혀 손실** |
| 더하기만 (모델 유지 + 올리기) | F1 0.182 → 0.222, Macro +0.0017 | 이득도 손실도 없다. dev 숫자만 오른다 |

**이것이 무라벨 카나리를 돌리는 이유다.** dev 재생만 보면 대상 밖 회귀가 0 인
깨끗한 +0.0091 이고 채택했을 것이다. 같은 검사가 과거에 `v8` 0.28 배·`v4` 0.34 배를
경고했고 그 제출에서 dev 이득의 절반이 사라졌다. 여기는 0.00 배다.

파일은 지우지 않고 남긴다. 규칙이 틀린 것이 아니라 **잴 대상이 dev 에만 있다**는
기록이고, 나중에 같은 축을 다시 제안하는 것을 막는 것이 이 파일의 용도다.
"""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path
from typing import Any, Dict, Optional

REPO = Path(__file__).resolve().parents[1]

# 「(일반경쟁·1억원미만)」 같은 공고 제목의 꼬리표.
TITLE_TAG = re.compile(r"\((일반경쟁|제한경쟁|지명경쟁|수의계약)\s*[·ㆍ]\s*(\d+)\s*(억|천만)\s*원?\s*미만\)")
UNIT = {"억": 100_000_000, "천만": 10_000_000}


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


def title_band_mismatch(rec: Dict[str, Any]) -> Optional[str]:
    """제목 꼬리표가 등록값과 어긋나면 그 꼬리표를 돌려준다. 어긋나지 않으면 None."""
    meta = rec.get("meta") or {}
    price = meta.get("입찰추정가격")
    for doc in rec.get("docs") or []:
        for tag in TITLE_TAG.finditer(doc.get("text") or ""):
            ceiling = int(tag.group(2)) * UNIT[tag.group(3)]
            if tag.group(1) != meta.get("계약방법"):
                return tag.group(0)
            if isinstance(price, (int, float)) and price >= ceiling:
                return tag.group(0)
    return None


def postprocess(judgment: Dict[str, Dict[str, Any]], rec: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    out = baseline().postprocess(judgment, rec)
    quote = title_band_mismatch(rec)
    out["v24"] = ({"위반여부": 1, "근거문구": quote} if quote
                  else {"위반여부": 0, "근거문구": ""})
    return out
