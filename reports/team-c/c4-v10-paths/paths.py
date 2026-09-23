"""C4 — v10 최종 양성 12건(TP 4 · FP 8)이 **어느 경로에서 나왔는지** 분해한다.

v10 을 쓸 수 있는 자리는 운영 코드에 둘뿐이다.
  1. **앞 단계 보존** — baseline(+SME 재검증)이 남긴 1 을 아무도 덮지 않는다
  2. **부재 판정** — `verify_document_requirements()` 가 `direct_production` 부재를 확인해 1 을 쓴다
     (`company_size_products()` 는 v12·v13 만 쓴다 — v10 을 안 건드린다)

경로가 TP 와 FP 를 가르면 그것이 새 재료다. 안 가르면 안 간다고 적는다.
**이 스크립트는 분해와 집계까지다. 규칙을 만들지 않는다.**

    py -X utf8 reports/team-c/c4-v10-paths/paths.py

모델을 부르지 않는다. 보관 회차의 원응답만 읽는다.
"""

from __future__ import annotations

import csv
import importlib.util
import io
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CASE = ROOT / "reports/runs/colab-1789902969401579900/dev-debug"
ITEM = "v10"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def read_responses():
    texts, chars = {}, {}
    for line in (CASE / "diagnostics.jsonl").read_text(encoding="utf-8").splitlines():
        event = json.loads(line)
        if (event.get("event") == "response" and event.get("status") == "valid"
                and "response_text" in event):
            texts.setdefault(event["phase"], {})[event["id"]] = event["response_text"]
        if event.get("event") == "company_size_input":
            chars[event["id"]] = event["max_chars"]
    return texts, chars


def main():
    script = load("submission", ROOT / "script.py")
    _, products = script.load_sme_reference(str(ROOT / "open/data"))
    settings = json.loads((CASE / "run_report.json").read_text(encoding="utf-8"))
    settings = settings["reproduction"]["settings"]
    legacy = {}
    if hasattr(script, "DOCUMENT_CHECK_ITEMS") and not settings.get("company_size_document_checks"):
        legacy["company_size_legacy"] = True
    if hasattr(script, "CLAUSE_QUOTE_MAX"):
        legacy["company_size_clause_quotes"] = bool(settings.get("company_size_clause_quotes"))
    if hasattr(script, "QUALIFICATION_ROLES"):
        legacy["company_size_qualification_role"] = bool(settings.get("company_size_qualification_role"))

    texts, chars = read_responses()
    with (ROOT / "open/dev_labels.csv").open(encoding="utf-8", newline="") as stream:
        truth = {r["id"]: r for r in csv.DictReader(stream)}

    rows, gate = [], []
    for rec in script.iter_records(str(ROOT / "open/dev.jsonl")):
        identifier = rec["id"]
        parsed, _ = script.parse_judgment(texts["baseline"][identifier])
        base = int((parsed.get(ITEM) or {}).get("위반여부", 0))

        for phase in getattr(script, "VERDICT_PHASES", ()):
            script.merge_extra_call(parsed, rec, phase,
                                    script.extra_call_items().get(phase) or (),
                                    texts.get(phase, {}).get(identifier))
        sme_text = texts.get("sme", {}).get(identifier)
        if sme_text is not None:
            focused, _ = script.parse_judgment(sme_text, expected_items=script.SME_ITEMS, sme=True)
            verified, _rejected = script.verify_sme(focused, rec, products, 16000)
            parsed.update(verified)
        after_sme = int((parsed.get(ITEM) or {}).get("위반여부", 0))

        wrote, facts, reason = None, {}, None
        company_text = texts.get("company_size", {}).get(identifier)
        if company_text is not None:
            focused, _ = script.parse_judgment(company_text,
                                               expected_items=script.COMPANY_SIZE_KEYS, **legacy)
            facts = focused["company_size"]
            verified, reason = script.verify_company_size(facts, rec, chars[identifier])
            if ITEM in verified:
                wrote = int(verified[ITEM]["위반여부"])
            parsed.update(verified)
        final = int(script.postprocess(parsed, rec)[ITEM]["위반여부"])

        # **거르기 전에 200건을 먼저 센다.** 양성만 남기고 세면 §4 의 전수 표에 산출물이
        # 없어진다 — 리뷰 [P2] 가 잡은 자리다.
        gate.append({"id": identifier.replace("PPS-DEV-", ""), "base": base,
                     "부재판정": wrote, "label": int(truth[identifier][ITEM]),
                     "final": final})
        if final != 1:
            continue

        if wrote == 1:
            path = "부재 판정"
        elif wrote == 0:
            path = "부재 판정(0)"     # 최종 1 이면 후처리가 되살린 것이다 — 있으면 따로 본다
        else:
            path = "앞 단계 보존"
        rows.append({
            "id": identifier.replace("PPS-DEV-", ""),
            "label": int(truth[identifier][ITEM]),
            "판정": "TP" if int(truth[identifier][ITEM]) == 1 else "FP",
            "경로": path,
            "base": base, "sme후": after_sme, "company": wrote, "reason": reason,
            "scope": facts.get("scope"),
            "direct_production": facts.get("direct_production"),
            "dp_quote_null": facts.get("direct_production_quote") is None,
            "requirements_complete": facts.get("requirements_complete"),
        })

    # 200건 전수를 (baseline 값, 부재 판정이 쓴 값, 라벨)로 묶는다. §4 표의 산출물이다.
    tally = {}
    for row in gate:
        key = f'base={row["base"]} · 부재판정={row["부재판정"]} · 라벨={row["label"]}'
        tally[key] = tally.get(key, 0) + 1

    payload = {"item": ITEM, "dev_n": len(gate), "positives": rows,
               "gate_tally": dict(sorted(tally.items())), "gate": gate}
    with io.open(Path(__file__).with_name("paths.json"), "w",
                 encoding="utf-8", newline="\n") as stream:
        json.dump(payload, stream, ensure_ascii=False, indent=1)
        stream.write("\n")

    print(f'{"공고":<6}{"판정":<5}{"경로":<14}{"base":>5}{"sme후":>6}{"company":>8}'
          f'{"scope":<13}{"dp":<9}{"완전":<6}{"reason"}')
    for row in sorted(rows, key=lambda r: (r["경로"], r["판정"], r["id"])):
        print(f'{row["id"]:<6}{row["판정"]:<5}{row["경로"]:<14}{row["base"]:>5}{row["sme후"]:>6}'
              f'{str(row["company"]):>8}  {str(row["scope"]):<13}{str(row["direct_production"]):<9}'
              f'{str(row["requirements_complete"]):<6}{row["reason"]}')

    print()
    print(f'{"경로":<14}{"n":>4}{"TP":>5}{"FP":>5}')
    for path in sorted({r["경로"] for r in rows}):
        group = [r for r in rows if r["경로"] == path]
        tp = sum(r["판정"] == "TP" for r in group)
        print(f'{path:<14}{len(group):>4}{tp:>5}{len(group) - tp:>5}')

    print(f'\n게이트 동작 전수 {len(gate)}건')
    for key, count in payload["gate_tally"].items():
        print(f'  {key:<44}{count:>4}')


if __name__ == "__main__":
    main()
