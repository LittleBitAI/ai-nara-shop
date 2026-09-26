"""C8 — scope 인용도 skeleton 대조로 살린다.

#142 가 v13 의 인용 검증에 `skeleton_quoted()` 를 들였다. PDF 추출이 숫자·괄호·따옴표를
다른 줄로 밀어 놓으면 원문 대조가 실패하는데, 그 문자들을 지운 뼈대로 맞춰 **문서 자신의
글자**를 돌려주는 함수다. 근거 계약이 그 인용을 원문에서 그대로 찾을 수 있게 남는다.

그 도구가 `scope_quote` 에는 안 쓰인다. `_company_size_bands()` 의 `quoted()` 는
`restore_spacing()` 까지만 보고, 실패하면 `unverified_scope` 로 기업규모 판정을 통째로
접는다.

dev 200건에서 `unverified_scope` 는 **11건**이고 그중 **1건(`041`)이 skeleton 으로
살아난다.** 그 한 건이 v18 양성을 놓치고 있다.

나머지 10건은 skeleton 으로도 안 산다. 인용이 `컴퓨터서버[4321150102]` ·
`잡석[1111169701]` 처럼 **품명과 품목번호**라, 원문 문장이 아니라 모델이 메타데이터에서
조합한 것으로 보인다. 그것은 인용 복원 문제가 아니라 다른 자리이고 이 후보가 안 건드린다.

**바꾸는 것은 `scope_quote` 하나다.** skeleton 이 찾아 준 원문 span 으로 갈아 끼우고
운영 판정을 그대로 받는다. 검증 규칙을 느슨하게 만들지 않는다 — `quoted()` 는 그대로
돌고, 통과하는 이유가 "원문에 실제로 그 글자가 있어서"인 것도 그대로다.

모델을 부르지 않는다. 추가 호출 0 · 추가 시간 0초.

재생:
    python -X utf8 tools/replay_run.py \
      --case reports/runs/colab-1790396310565903096/dev-debug \
      --script <기준 커밋의 script.py> \
      --candidate experiments/c8_scope_skeleton_candidate.py --output-dir <새 경로>
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def baseline():
    """재생기가 읽은 제출 코드를 집는다. 단독 import 면 저장소 루트의 것을 읽는다."""
    submitted = sys.modules.get("submission")
    if submitted is not None:
        return submitted
    spec = importlib.util.spec_from_file_location("baseline_script", ROOT / "script.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def repaired_scope_quote(script, facts: dict[str, Any], rec: dict[str, Any], visible: str):
    """원문 대조가 실패한 `scope_quote` 를 skeleton 으로 살린다. 못 살리면 None."""
    quote = facts.get("scope_quote")
    if not quote:
        return None
    # 운영 검증을 먼저 그대로 밟는다. 통과하면 건드릴 이유가 없다.
    fixed = script.restore_spacing(quote, rec, visible) or quote
    if (fixed and fixed.strip() and fixed in visible
            and any(fixed in doc["text"] for doc in rec["docs"])):
        return None
    return script.skeleton_quoted(quote, rec, visible)


def verify_company_size(facts: dict[str, Any], rec: dict[str, Any], max_chars: int):
    """살릴 수 있는 scope 인용만 갈아 끼우고 운영 판정을 그대로 받는다."""
    script = baseline()
    if not hasattr(script, "skeleton_quoted"):
        return script.verify_company_size(facts, rec, max_chars)
    visible = script.build_context(rec, max_chars)
    repaired = repaired_scope_quote(script, facts, rec, visible)
    if repaired is None:
        return script.verify_company_size(facts, rec, max_chars)
    return script.verify_company_size(dict(facts, scope_quote=repaired), rec, max_chars)
