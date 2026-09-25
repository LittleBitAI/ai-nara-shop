"""C6 세 규칙의 **적용 대상**과 **바뀐 셀**을 따로 센다. 모델을 부르지 않는다.

**왜 둘을 따로 세나.** "셀이 안 바뀌었다"에는 서로 다른 두 가지가 섞여 있다.

  1. **적용 대상이 0건이다** — 그 회차의 모델 출력에 규칙의 조건을 만족하는 공고가 없다.
     이 회차는 후보를 **안 잰 것**이고, 가설에 대해 아무것도 말하지 않는다. 판정 보류.
  2. **대상이 있는데 셀이 그대로다** — 규칙이 돌았고 아무것도 못 바꿨다. **가설 기각**이다
     (`.wiki/gpu-before-review`).

둘을 섞으면 "대상이 없었다"를 기각으로 적거나, 반대로 진짜 기각을 "다음 회차에서 보자"로
미룬다. C5 의 v13 후보가 1번에 해당했다 — dev 에서 0셀이지만 무라벨 5,500건에서는 6건을
닫는다. 규칙이 죽은 것이 아니라 그 출력에 대상이 없었다.

    py -X utf8 reports/team-c/c6-dev-macro/applicability.py --case <회차>/dev-debug

**판정 코드를 커밋으로 고정한다.** 적용 대상은 **기준 코드**가 무엇에 적용될 뻔했는지이므로
`BASE_REV` 의 `script.py` 로 센다. 작업 트리 판을 쓰지 않는다.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
# 이 폴더의 수를 낸 판정 코드. 보고서 §1 의 기준 commit 과 같아야 한다.
BASE_REV = "9038380"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def load_pinned(rev):
    """`rev:script.py` 를 임시 파일로 꺼내 모듈로 싣는다. 작업 트리 판을 안 쓴다."""
    source = subprocess.run(["git", "-C", str(ROOT), "show", f"{rev}:script.py"],
                            capture_output=True, check=True).stdout
    path = Path(tempfile.mkdtemp(prefix=f"script-{rev}-")) / "script.py"
    path.write_bytes(source)
    return load("submission", path)


def read_responses(case):
    texts, chars = {}, {}
    for line in (case / "diagnostics.jsonl").read_text(encoding="utf-8").splitlines():
        event = json.loads(line)
        if (event.get("event") == "response" and event.get("status") == "valid"
                and "response_text" in event):
            texts.setdefault(event["phase"], {})[event["id"]] = event["response_text"]
        if event.get("event") == "company_size_input":
            chars[event["id"]] = event["max_chars"]
    return texts, chars


def legacy_flags(script, case):
    settings = json.loads((case / "run_report.json").read_text(encoding="utf-8"))
    settings = settings["reproduction"]["settings"]
    flags = {}
    if hasattr(script, "DOCUMENT_CHECK_ITEMS") and not settings.get("company_size_document_checks"):
        flags["company_size_legacy"] = True
    if hasattr(script, "CLAUSE_QUOTE_MAX"):
        flags["company_size_clause_quotes"] = bool(settings.get("company_size_clause_quotes"))
    if hasattr(script, "QUALIFICATION_ROLES"):
        flags["company_size_qualification_role"] = bool(settings.get("company_size_qualification_role"))
    return flags


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--case", required=True,
                        help="원응답이 있는 회차 폴더, 예: reports/runs/<run-id>/dev-debug")
    parser.add_argument("--input", default=str(ROOT / "open/dev.jsonl"))
    parser.add_argument("--rev", default=BASE_REV,
                        help="판정에 쓸 script.py 의 커밋. 기본은 이 폴더가 고정한 것")
    args = parser.parse_args(argv)

    case = Path(args.case)
    script = load_pinned(args.rev)
    narrow = load("c6_band_no_demand_narrow_candidate",
                  ROOT / "experiments/c6_band_no_demand_narrow_candidate.py")
    role = load("c6_v16_role_none_candidate",
                ROOT / "experiments/c6_v16_role_none_candidate.py")
    absence = load("c5_v11_absence_signal_candidate",
                   ROOT / "experiments/c5_v11_absence_signal_candidate.py")

    texts, chars = read_responses(case)
    legacy = legacy_flags(script, case)

    # 규칙마다 (적용 대상, 그중 셀이 실제로 바뀐 수)를 센다.
    applicable = {"v18": 0, "v16": 0, "v11": 0}
    flipped = {"v18": 0, "v16": 0, "v11": 0}
    notices = 0

    for rec in script.iter_records(args.input):
        identifier = rec["id"]
        company_text = texts.get("company_size", {}).get(identifier)
        if company_text is None:
            continue
        notices += 1
        focused, _ = script.parse_judgment(company_text,
                                           expected_items=script.COMPANY_SIZE_KEYS, **legacy)
        facts = focused["company_size"]
        max_chars = chars[identifier]
        out, reason = script.verify_company_size(facts, rec, max_chars)

        # 1. v18 — 직생 요구 문장이 없는데 scope 가 competitive 다.
        if (reason != "unverified_scope" and facts.get("scope") == narrow.CONTESTED_SCOPE
                and narrow.demand_absent(script, rec)):
            applicable["v18"] += 1
            assumed, _r = script.verify_company_size(
                dict(facts, scope=narrow.ASSUMED_SCOPE), rec, max_chars)
            cell = assumed.get("v18")
            if cell and cell["위반여부"] == 1 and (out.get("v18") or {}).get("위반여부") != 1:
                flipped["v18"] += 1

        # 2. v16 — 자격 문장의 역할이 미정이다. 결정표가 v16 을 올린 것만 대상이다.
        if facts.get("qualification_role") == role.UNDECIDED_ROLE:
            if (out.get("v16") or {}).get("위반여부") == 1:
                applicable["v16"] += 1
                flipped["v16"] += 1        # 대상이면 반드시 바뀐다 — 1 을 0 으로 쓴다

        # 3. v11 — v10 부재가 확인됐고 중소 허용 문구가 없다.
        if reason != "unverified_scope":
            visible = script.build_context(rec, max_chars)
            if ((out.get("v11") or {}).get("위반여부") != 1
                    and absence.absence_confirmed(script, facts, rec, visible)
                    and not absence.sme_allowed(script, rec)):
                applicable["v11"] += 1
                flipped["v11"] += 1        # 대상이면 반드시 바뀐다 — 0 을 1 로 쓴다

    print(f"회차 {case}")
    print(f"판정 코드 {args.rev} · company 응답이 있는 공고 {notices}건\n")
    print(f'{"규칙":<8}{"적용 대상":>9}{"바뀐 셀":>9}   판정')
    verdicts = {}
    for item in ("v18", "v16", "v11"):
        if applicable[item] == 0:
            verdict = "대상 없음 — 이 회차는 이 규칙을 안 쟀다 (판정 보류)"
        elif flipped[item] == 0:
            verdict = "대상이 있는데 안 바뀌었다 — 가설 기각"
        else:
            verdict = "발동했다"
        verdicts[item] = verdict
        print(f'{item:<8}{applicable[item]:>9}{flipped[item]:>9}   {verdict}')

    print("\n기준 Z 는 이 표로 읽는다. **적용 대상 0 은 기각이 아니다** — 그 회차가 규칙을")
    print("안 잰 것이고, 가설에 대해 아무것도 말하지 않는다. 대상이 있는데 0셀이면 기각이다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
