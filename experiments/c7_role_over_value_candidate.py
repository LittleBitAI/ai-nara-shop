"""C7 — 역할과 값이 싸우면 역할을 믿는다.

운영 `verify_company_size()` 는 `qualification_role` 로 `qualification` 을 검증한다.

    allowed = ("small_only", "sme_allowed") if role == "eligibility" else (
        ("unrestricted",) if role in ("checklist", "legal_reference", "none") else ())
    if facts.get("qualification") not in allowed:
        facts["qualification"] = "unknown"

즉 **역할이 "참가자격 조항이 아니다"(checklist · legal_reference · none)라고 말하면
`unrestricted` 만 받는다.** 그 자리에 모델이 `sme_allowed` 나 `small_only` 를 쓰면
값을 버리고 `unknown` 으로 두어 판정을 보류한다.

이 후보가 묻는 것은 그 비대칭이다. **역할이 이미 "제한 조항이 아니다"라고 말했다면
제한은 없는 것이다.** 모른다고 둘 일이 아니라 `unrestricted` 로 읽을 일이다.
운영 코드가 그 역할들에서 `unrestricted` 만 허용하는 것 자체가 "이 역할이면 제한이
아니다"를 이미 인정한 것이고, 이 후보는 그 논리를 끝까지 민다.

**적용 범위가 좁다.** dev 200건에서 역할과 값이 어긋나는 공고는 **2건**이다
(`checklist` × `sme_allowed`). 둘 다 지금은 `unknown` 이 되어 각각
`unverified_qualification` 과 `outside_general_scope` 로 막힌다.

**표본이 2건이라 dev 라벨 기반에 가깝다.** 근거가 조문이 아니라 운영 코드의 기존
논리이고, 그 논리가 옳다는 것을 dev 두 건 말고는 확인할 자료가 없다. 방침이
되돌아가면 이 후보부터 뺀다.

`eligibility` 는 안 건드린다. 그쪽은 `unrestricted` 가 어긋나는 값인데, 자격 조항에
"제한 없음"이라고 쓰는 것은 실제로 있을 수 있어 같은 논리가 안 선다.

모델을 부르지 않는다. 추가 호출 0 · 추가 시간 0초.

재생:
    python -X utf8 tools/replay_run.py \
      --case reports/runs/colab-1790396310565903096/dev-debug \
      --script <기준 커밋의 script.py> \
      --candidate experiments/c7_role_over_value_candidate.py --output-dir <새 경로>
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# 이 역할들은 "그 문장이 참가자격 제한 조항이 아니다" 를 뜻한다.
NON_RESTRICTING_ROLES = ("checklist", "legal_reference", "none")
# 그 역할에서 운영 코드가 받는 유일한 값.
ASSUMED = "unrestricted"


def baseline():
    """재생기가 읽은 제출 코드를 집는다. 단독 import 면 저장소 루트의 것을 읽는다."""
    submitted = sys.modules.get("submission")
    if submitted is not None:
        return submitted
    spec = importlib.util.spec_from_file_location("baseline_script", ROOT / "script.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def role_overrides_value(facts: dict[str, Any]) -> bool:
    """역할이 제한 아님을 말하는데 값이 제한을 말하는가. 적용 대상 판별."""
    return (facts.get("qualification_role") in NON_RESTRICTING_ROLES
            and facts.get("qualification") not in (ASSUMED, "unknown"))


def verify_company_size(facts: dict[str, Any], rec: dict[str, Any], max_chars: int):
    """역할이 제한 아님을 말하면 값을 그쪽으로 맞춰 운영 판정을 다시 받는다.

    운영 함수를 그대로 부른다. 규칙을 옮겨 적지 않으므로 결정표가 바뀌면 이 후보도
    같이 바뀐다. 바꾸는 것은 들어가는 `qualification` 하나뿐이다.
    """
    script = baseline()
    if not role_overrides_value(facts):
        return script.verify_company_size(facts, rec, max_chars)
    return script.verify_company_size(dict(facts, qualification=ASSUMED), rec, max_chars)
