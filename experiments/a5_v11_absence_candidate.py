"""A5 H2: 검증된 company_size 부재 관측만 v11에 추가 연결한다.

판로지원법 제7조①의 기업 제한 부재는 직생 요구 문장 유무와 독립이다.
H1 표기 확대는 포함하지 않는다. 새 모델 호출·프롬프트 변경은 없다.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import script


def observed_absence(facts, rec, max_chars, base=script):
    if (facts.get("scope") != "competitive"
            or facts.get("qualification") != "unrestricted"
            or facts.get("qualification_role") not in ("none", "checklist", "legal_reference")
            or facts.get("qualification_complete") != "yes"
            or facts.get("requirements_complete") != "yes"
            or facts.get("priority_exception") != "no"
            or facts.get("size_exception") != "none"
            or rec.get("input_completeness", {}).get("완전관측") is not True
            or any((rec.get("dropped_doc_counts") or {}).values())):
        return False
    visible = base.build_context(rec, max_chars)
    if "[Truncated documents; unseen remainder]" in visible or "[Missing documents]" in visible:
        return False
    for key in ("scope_quote", "qualification_quote"):
        quote = facts.get(key)
        quote = base.restore_spacing(quote, rec, visible) or quote
        if not (quote and quote.strip() and quote in visible
                and any(quote in doc["text"] for doc in rec["docs"])):
            return False
    return True


def verify_company_size(facts, rec, max_chars):
    base = sys.modules.get("submission") or sys.modules.get("run_submission") or script
    out, reason = base.verify_company_size(facts, rec, max_chars)
    if observed_absence(facts, rec, max_chars, base):
        out = {**out, "v11": {"위반여부": 1, "근거문구": None}}
    return out, reason


def demo():
    from copy import deepcopy
    from types import SimpleNamespace
    from unittest.mock import patch

    text = "행사기획및대행서비스\n참가자격: 등록한 사업자이며 기업규모 제한은 명시하지 않는다."
    rec = dict(docs=[dict(type="공고문", doc_id="D0", text=text)],
               input_completeness={"완전관측": True}, dropped_doc_counts={})
    facts = dict(scope="competitive", scope_quote="행사기획및대행서비스",
                 qualification="unrestricted", qualification_role="none",
                 qualification_quote=text.splitlines()[1], qualification_complete="yes",
                 requirements_complete="yes", priority_exception="no", size_exception="none")
    assert observed_absence(facts, rec, 1000)
    for key, value in (("qualification", "sme_allowed"), ("qualification_role", "eligibility"),
                       ("qualification_complete", "no"), ("requirements_complete", "no"),
                       ("priority_exception", "unknown"), ("size_exception", "joint_small"),
                       ("scope_quote", "존재하지 않는 품목"), ("qualification_quote", None)):
        assert not observed_absence({**facts, key: value}, rec, 1000), key
    assert not observed_absence(facts, rec, 20)
    assert not observed_absence(facts, {**rec, "dropped_doc_counts": {"제안요청서": 1}}, 1000)
    assert not observed_absence(facts, {**rec, "input_completeness": {}}, 1000)
    original = {v: {"위반여부": 0, "근거문구": None} for v in script.ITEMS if v != "v11"}
    saved = deepcopy(original)
    active = SimpleNamespace(verify_company_size=lambda *args: (original, "base-reason"),
                             build_context=script.build_context, restore_spacing=script.restore_spacing)
    with patch.dict(sys.modules, {"submission": active}):
        out, reason = verify_company_size(facts, rec, 1000)
    assert out["v11"] == {"위반여부": 1, "근거문구": None}
    assert {k: v for k, v in out.items() if k != "v11"} == saved == original
    assert reason == "base-reason"
    print("A5 H2 absence self-check passed")


if __name__ == "__main__":
    demo()
