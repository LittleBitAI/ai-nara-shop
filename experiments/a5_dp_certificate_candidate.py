"""A5 H1: 직접생산증명서의 '확인' 생략도 같은 요구로 읽는 후처리 후보.

법적 조건은 판로지원법 제7조·제9조, 표기 변형은 dev 원문에서 관측했다.
공유 추출기의 모든 호출자에 적용하며 script.py는 변경하지 않는다.
"""

import re
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import script


def pattern(base):
    return re.compile(base.DP_DEMAND.pattern.replace(
        r"확인\s*(?:증명서|서류)?", r"(?:확인\s*(?:증명서|서류)?|증명서)"))


def postprocess(judgment, rec):
    base = sys.modules.get("submission") or sys.modules.get("run_submission") or script
    with patch.object(base, "DP_DEMAND", pattern(base)):
        return base.postprocess(judgment, rec)


def verify_company_size(facts, rec, max_chars):
    base = sys.modules.get("submission") or sys.modules.get("run_submission") or script
    with patch.object(base, "DP_DEMAND", pattern(base)):
        return base.verify_company_size(facts, rec, max_chars)


def demo():
    original = script.DP_DEMAND
    with patch.object(script, "DP_DEMAND", pattern(script)):
        for text in ("직접생산증명서를 소지한 업체", "직접생산확인증명서를 보유한 업체"):
            assert script.direct_production_demand({"docs": [{"text": text}]})[0] == text
        for text in ("직접생산 확인기준을 위반한 경우 제재", "직접생산 설비를 보유한 업체"):
            assert script.direct_production_demand({"docs": [{"text": text}]})[0] is None
    assert script.DP_DEMAND is original
    active = SimpleNamespace(DP_DEMAND=original,
                             postprocess=lambda *args: "active postprocess",
                             verify_company_size=lambda *args: "active verifier")
    with patch.dict(sys.modules, {"submission": active}):
        assert postprocess({}, {}) == "active postprocess"
        assert verify_company_size({}, {}, 1) == "active verifier"
    assert active.DP_DEMAND is original
    print("A5 certificate self-check passed")


if __name__ == "__main__":
    demo()
