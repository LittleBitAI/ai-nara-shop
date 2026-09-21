"""후처리 후보 — 고시 뒷받침 없는 `competitive` 는 v14~v18 을 **닫지 못한다**. **기각됨.**

모델 뒤 단계만 바꾼다. `tools/replay_run.py --candidate` 로 갈아 끼운다. GPU 를 쓰지 않는다.

**결과: `18f07e5` 회차 `colab-1789902969401579900` 재생에서 0.593846165415 → 0.593370428562,
`-0.000476`. 채택하지 않는다.** 바뀐 셀 9개가 전부 `BAND_ITEMS` 안이고 밴드 밖 0셀이다.
TP +2(v14·v18), FP +7(v17 넷·v14·v16·v18). 아래 「기각의 뜻」에 읽는 법을 적었다.

## 왜

`_company_size_bands` 는 `scope` 가 `competitive`/`other` 면 v14~v18 다섯 칸에 **확정 0** 을
쓰고 `outside_general_scope` 로 끝낸다. 그 확정 0 의 근거가 모델의 3지선다 enum 하나다.

**그 enum 은 보정돼 있지 않다.** 같은 dev 200건에서 두 번 측정했다.

| 회차 | `competitive` 발화 | v10·v11·v13 양성 15건 재현율 | 정밀도 |
| --- | ---: | ---: | ---: |
| 합본 `0a172a2` ([competitive-gate](../reports/team-c/competitive-gate/README.md)) | 7 / 200 | **0 / 15** | — |
| a5-v18 회차2 control (`44f5e4b`) | **79 / 200** | 15 / 15 | **0.19** |

한 번은 전혀 안 열리고 한 번은 40% 에 쏜다. 그 사이에 바뀐 것은 프롬프트뿐이다.
그리고 [A5 v18 파일럿](../reports/team-c/a5-v18-scope-review/results.md)이 **같은 호출 안에서
더 꼼꼼한 말로 범위를 다시 물어도 199/200 이 똑같은 답**임을 800응답으로 보였다.
**이 필드는 다시 물어서 고쳐지지 않는다.**

**같은 필드가 서로 반대인 두 일을 한다.** v10·v11·v13 은 `competitive` 여야 열리고,
v14·v15·v17·v18 은 `general` 이어야 열린다. 79건이 competitive 라서
일반물품 항목 정답 양성 27건 중 6건이 닫힌다.

## 무엇을 바꾸나

**여는 데 요구하는 근거를 닫는 데도 똑같이 요구한다.** 바로 아래 줄의
`competitive_by_catalogue` 가 이미 반대 방향으로 그 일을 한다 — "모델이 general 이라 해도
카탈로그가 경쟁제품이라면 그쪽을 믿는다". 여기서는 대칭으로, 카탈로그가 뒷받침하지 않는
`competitive` 는 밴드를 닫지 못하게 한다. 그 공고의 v14~v18 만 결정표로 되돌리고,
**나머지 23항목은 원래 결과 그대로다** — `scope` 를 직접 소비하는 v10·v12·v13·v20 포함.

뒷받침의 정의는 새로 만들지 않는다. 기존 `competitive_product()` 를 그대로 쓴다 —
`특이사항` 의 추정가격 상한까지 본다. 품명번호는 `sme_product_lookup()` 의 강한 출처
(메타 등록 코드·공고 본문 코드)만 쓴다. 품명 문자열 포함 매칭은 넣지 않는다 —
`len(name) >= 4 and name in flat` 는 오탐 쪽으로 넓다.

## 실측 (보관 원응답 CPU 재생, GPU 0초, 회차 churn 없음)

```
python -X utf8 tools/replay_run.py --case reports/runs/colab-1789902969401579900/dev-debug \
    [--candidate experiments/a6_unbacked_competitive.py] --output-dir <새 폴더>
python -X utf8 tools/score.py --truth open/dev_labels.csv --pred <그 폴더>/submission.csv --output-dir <새 폴더>
```

기준 재생은 회차 CSV 와 바이트 동일하고, 후보 재생은 두 번 돌려 바이트 동일하다(결정적).

| 항목 | 기준 TP/FP/FN | F1 | 후보 TP/FP/FN | F1 |
| --- | --- | ---: | --- | ---: |
| v14 | 7/2/1 | 0.824 | 8/3/0 | **0.842** |
| v16 | 4/2/2 | 0.667 | 4/3/2 | 0.615 |
| v17 | 5/6/1 | 0.588 | 5/**10**/1 | 0.476 |
| v18 | 1/2/6 | 0.200 | 2/3/5 | **0.333** |
| **Macro** | | **0.593846165415** | | **0.593370428562** |

## 기각의 뜻 — 이 방향은 후처리로 안 된다

**v17 오탐 넷이 v18·v14 정탐 둘을 덮는다.** 밴드를 여는 29건은 실제로 범위가 모호한 공고이고,
다섯 칸이 한꺼번에 열리므로 부재탐지(v16·v18)의 이득과 적극판정(v14·v15·v17)의 손해가 같이 온다.

**이긴 항목만 골라 남기지 않는다.** 항목당 양성 5~8건 위에서 다섯 칸 중 고르는 것은
`a4_scope_gate_candidate` 가 적어 둔 그 dev 과적합 경로다. 부분집합 탐색을 하지 않았다.

**읽을 것은 따로 있다. `scope` 는 양방향으로 정보가 없다.** 두 회차에서 같은 값이 나온다 —
`colab-1789902969401579900` competitive 78/200, `a5-v18-…885632` 회차2 control 79/200,
둘 다 정밀도 0.19 · 재현율 1.00 · 일반물품 양성 27건 중 6건 차단. churn 이 아니라 안정된 성질이다.
정밀도 0.19 짜리 필드는 **닫는 쪽을 막아도, 여는 쪽을 막아도** 고쳐지지 않는다.
필드 자체가 정보를 실어야 하고, 그것은 프롬프트·스키마 변경이라 이 경로로는 못 잰다.

## 안 한 것

- **확정 0 대신 baseline 보존**(밴드 칸을 아예 안 쓰는 변형)은 재 보니 **변화 0셀**이다.
  그 29건의 baseline v14~v18 이 전부 0이라, 결정표가 실제로 새 판정을 만들고 있다.
- **강한 후보의 존재만 보는 변형**은 `특이사항` 상한을 안 봐서 v14 미탐 1건을 못 살린다.
- `scope` 자체를 코드로 다시 정하지 않는다. 이 후보는 **닫는 쪽만** 건드린다.
  여는 쪽(v10·v11·v13 의 FP 20건)은 모델이 무엇을 관측했는지를 묻는 별도 GPU 가설이다.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any, Dict, Tuple

REPO = Path(__file__).resolve().parents[1]

# 품명번호를 믿을 수 있는 출처. 메타 등록값과 공고 본문이 적은 10자리 코드다.
STRONG_MATCH_SOURCES = ("메타코드", "문서코드")

_SCRIPT = None


def baseline():
    """제출 코드를 한 번만 읽어 돌려준다. replay_run 이 넘긴 것이 있으면 그것을 쓴다."""
    global _SCRIPT
    if _SCRIPT is None:
        _SCRIPT = sys.modules.get("run_submission") or sys.modules.get("submission")
    if _SCRIPT is None:
        spec = importlib.util.spec_from_file_location("baseline_script", REPO / "script.py")
        _SCRIPT = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_SCRIPT)
    return _SCRIPT


def observed_product_codes(rec: Dict[str, Any], max_chars: int) -> set:
    """이 공고에서 실제로 관측된 고시 세부품명번호. 품명 문자열 추정은 넣지 않는다."""
    script = baseline()
    visible = script.build_context(rec, max_chars)
    lookup = script.sme_product_lookup(rec, visible, script._PRODUCTS)
    return {p["세부품명번호"] for p in lookup["일치후보"]
            if p["일치출처"] in STRONG_MATCH_SOURCES}


def catalogue_backed(rec: Dict[str, Any], max_chars: int) -> bool:
    """제공 고시가 이 공고를 경쟁제품이라고 말하는가. 기존 `competitive_product` 를 그대로 쓴다."""
    script = baseline()
    return script.competitive_product(rec, observed_product_codes(rec, max_chars)) is True


def verify_company_size(facts: Dict[str, Any], rec: Dict[str, Any],
                        max_chars: int) -> Tuple[Dict[str, Dict[str, Any]], str]:
    script = baseline()
    out, reason = script.verify_company_size(facts, rec, max_chars)
    if reason != "outside_general_scope" or facts.get("scope") != "competitive":
        return out, reason                      # other·다른 반환 지점은 건드리지 않는다
    if catalogue_backed(rec, max_chars):
        return out, reason                      # 고시가 뒷받침한다 — 원래대로 닫는다
    general, _ = script.verify_company_size(dict(facts, scope="general"), rec, max_chars)
    merged = dict(out)                          # 나머지 23항목은 원래 결과 그대로
    for item in script.BAND_ITEMS:
        merged.pop(item, None)
        if item in general:
            merged[item] = general[item]
    return merged, "unbacked_competitive"
