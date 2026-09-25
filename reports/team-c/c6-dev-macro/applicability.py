"""C6 세 규칙을 **세 층으로** 센다 — 조건 충족 · 변경 기회 · 실제 변경. 모델을 안 부른다.

**왜 세 층인가.** 첫 판은 "적용 대상"과 "바뀐 셀" 둘만 셌는데, **적용 대상이 변경 기회를
뜻하지 않는다.** v18 규칙은 고정 원응답에서 게이트를 **38건** 통과하지만 그중 결정표가
v18 을 세우는 것은 **3건**뿐이다. 나머지 35건은 `general` 로 다시 밟아도 금액·자격·관측
조건에서 막혀 애초에 바뀔 수가 없다.

    decided 인데 v18 이 안 선다   23
    unverified_qualification      9
    absence_not_observable        3

그래서 "대상 38건이 있는데 0셀"을 기각으로 읽으면 **규칙이 아니라 회차를 벌한다.** 새
회차에서 게이트 통과가 38건이어도 그중 v18 이 설 공고가 0이면 그것은 가설에 대해 아무
말도 하지 않는다.

  1. **조건 충족** — 규칙의 게이트를 통과했다. 넓이이고, 판정에 직접 쓰지 않는다
  2. **변경 기회** — 그중 규칙이 **1 을 쓰겠다고 판단한** 것. 현재 값과 무관하다.
     **0 이면 이 회차는 규칙을 안 쟀다** — 판정 보류
  3. **실제 변경** — 그중 현재 값이 달라 셀이 정말 바뀐 것.
     기회가 있는데 0 이면 **다른 경로가 이미 그 셀을 올렸다**(중복) — 역시 판정 보류

**"안 움직였다"는 어느 층에서든 기각이 아니다.** 기각은 셀이 실제로 바뀌었는데 그 항목의
TP/FP/FN 이 안 나아질 때다(`.wiki/gpu-before-review`) — 그것은 채점이 보므로 여기서
찍지 않는다. `RUN-REQUEST.md` §4-2 의 Z3 이다.

C5 의 v13 후보가 2번에 해당했다 — dev 에서 0셀이지만 무라벨 5,500건에서는 6건을 닫는다.
규칙이 죽은 것이 아니라 그 출력에 겹치는 대상이 없었다.

    py -X utf8 reports/team-c/c6-dev-macro/applicability.py --case <회차>/dev-debug

**판정 코드를 커밋으로 고정한다.** 세 층 모두 **기준 코드**가 무엇에 적용될 뻔했는지이므로
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
BASE_REV = "c68eb00"


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

    # 규칙마다 세 층을 센다 — 조건 충족 · 변경 기회 · 실제 변경.
    gate = {"v18": 0, "v16": 0, "v11": 0}
    opportunity = {"v18": 0, "v16": 0, "v11": 0}
    flipped = {"v18": 0, "v16": 0, "v11": 0}
    # 게이트는 통과했는데 기회가 아닌 것들이 어디서 막혔나. 진단용이다.
    blocked = {}
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
        #    **게이트 통과는 변경 기회가 아니다.** `general` 로 다시 밟았을 때 결정표가
        #    v18 을 세우는 것만 기회이고, 그중 현재 값이 1 이 아닌 것만 실제 변경이다.
        if (reason != "unverified_scope" and facts.get("scope") == narrow.CONTESTED_SCOPE
                and narrow.demand_absent(script, rec)):
            gate["v18"] += 1
            assumed, assumed_reason = script.verify_company_size(
                dict(facts, scope=narrow.ASSUMED_SCOPE), rec, max_chars)
            cell = assumed.get("v18")
            if cell and cell["위반여부"] == 1:
                opportunity["v18"] += 1
                if (out.get("v18") or {}).get("위반여부") != 1:
                    flipped["v18"] += 1
            else:
                where = (assumed_reason if assumed_reason != "decided"
                         else "decided 인데 v18 이 안 선다")
                blocked[where] = blocked.get(where, 0) + 1

        # 2. v16 — 자격 문장의 역할이 미정이다. 결정표가 v16 을 올린 것만 대상이다.
        #    이 규칙은 게이트 조건에 "지금 1 이다"가 들어 있어 세 층이 같다.
        if facts.get("qualification_role") == role.UNDECIDED_ROLE:
            if (out.get("v16") or {}).get("위반여부") == 1:
                gate["v16"] += 1
                opportunity["v16"] += 1
                flipped["v16"] += 1        # 1 을 0 으로 쓴다

        # 3. v11 — v10 부재가 확인됐고 중소 허용 문구가 없다.
        #    이 규칙도 게이트 조건에 "지금 1 이 아니다"가 들어 있어 세 층이 같다.
        if reason != "unverified_scope":
            visible = script.build_context(rec, max_chars)
            if ((out.get("v11") or {}).get("위반여부") != 1
                    and absence.absence_confirmed(script, facts, rec, visible)
                    and not absence.sme_allowed(script, rec)):
                gate["v11"] += 1
                opportunity["v11"] += 1
                flipped["v11"] += 1        # 0 을 1 로 쓴다

    print(f"회차 {case}")
    print(f"판정 코드 {args.rev} · company 응답이 있는 공고 {notices}건\n")
    print(f'{"규칙":<8}{"조건 충족":>10}{"변경 기회":>10}{"실제 변경":>10}   판정')
    for item in ("v18", "v16", "v11"):
        if opportunity[item] == 0:
            verdict = "변경 기회 없음 — 이 회차는 이 규칙을 안 쟀다 (Z1, 판정 보류)"
        elif flipped[item] == 0:
            verdict = "기회가 이미 1 이었다 — 다른 경로가 먼저 올렸다 (Z2, 판정 보류)"
        else:
            verdict = "발동했다"
        print(f'{item:<8}{gate[item]:>10}{opportunity[item]:>10}'
              f'{flipped[item]:>10}   {verdict}')

    if blocked:
        print("\nv18 게이트는 통과했지만 기회가 아닌 것들이 막힌 곳")
        for where, count in sorted(blocked.items(), key=lambda pair: -pair[1]):
            print(f"  {where:<36}{count:>4}")

    print("\n**어느 층에서 0 이 나오든 기각이 아니다.** 그 회차가 규칙을 안 쟀거나 다른")
    print("경로와 겹친 것이고, 가설에 대해 아무 말도 하지 않는다. 기각은 셀이 실제로")
    print("바뀌었는데 그 항목의 TP/FP/FN 이 안 나아질 때다 — 채점이 본다(§4-2 의 Z3).")
    print("**조건 충족 수는 넓이일 뿐 판정에 쓰지 않는다.**")
    return 0


if __name__ == "__main__":
    sys.exit(main())
