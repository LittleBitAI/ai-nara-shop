"""C2 — v13 합성 후보의 **적용 대상 건수**와 **실제 바뀐 셀 수**를 따로 센다.

둘은 다른 수다. PR #85 당시 dev 200건에서 118건 대 1셀이었고, 베이스가 세 번 움직인
지금도 같은지 본다. 넓이 자체는 위험이 아니다 — 위험은 적용 대상에 앞 단계 양성이
겹치는 자리에 있다.

    py -X utf8 reports/team-c/c2-v13-remeasure/firing.py

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
ITEM = "v13"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def main():
    script = load("submission", ROOT / "script.py")
    candidate = load("c_v13_merge_candidate", ROOT / "experiments/c_v13_merge_candidate.py")
    script.load_sme_reference(str(ROOT / "open/data"))
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

    texts, chars = {}, {}
    for line in (CASE / "diagnostics.jsonl").read_text(encoding="utf-8").splitlines():
        event = json.loads(line)
        if (event.get("event") == "response" and event.get("status") == "valid"
                and "response_text" in event):
            texts.setdefault(event["phase"], {})[event["id"]] = event["response_text"]
        if event.get("event") == "company_size_input":
            chars[event["id"]] = event["max_chars"]

    with (ROOT / "open/dev_labels.csv").open(encoding="utf-8", newline="") as stream:
        truth = {r["id"]: r for r in csv.DictReader(stream)}

    applicable, changed, overlap = [], [], []
    for rec in script.iter_records(str(ROOT / "open/dev.jsonl")):
        identifier = rec["id"]
        parsed, _ = script.parse_judgment(texts["baseline"][identifier])
        for phase in getattr(script, "VERDICT_PHASES", ()):
            script.merge_extra_call(parsed, rec, phase,
                                    script.extra_call_items().get(phase) or (),
                                    texts.get(phase, {}).get(identifier))
        sme_text = texts.get("sme", {}).get(identifier)
        if sme_text is not None:
            focused, _ = script.parse_judgment(sme_text, expected_items=script.SME_ITEMS, sme=True)
            verified, _rejected = script.verify_sme(focused, rec, products, 16000)
            parsed.update(verified)

        company_text = texts.get("company_size", {}).get(identifier)
        if company_text is None:
            continue
        focused, _ = script.parse_judgment(company_text,
                                           expected_items=script.COMPANY_SIZE_KEYS, **legacy)
        facts = focused["company_size"]
        head_out, reason = script.verify_company_size(facts, rec, chars[identifier])
        wrote = ITEM in head_out

        if candidate.contradicts(facts, reason, wrote):
            # 앞 단계(baseline+SME)가 이 공고에 남긴 v13 값. 이것이 1 이면 후보가 닫는다.
            before = int((parsed.get(ITEM) or {}).get("위반여부", 0))
            applicable.append(identifier)
            if before == 1:
                overlap.append({"id": identifier, "label": truth[identifier][ITEM],
                                "scope": facts.get("scope"), "reason": reason})
                changed.append(identifier)

    out = {"dev_n": 200, "with_company_response": len(texts.get("company_size", {})),
           "applicable": len(applicable), "changed_cells": len(changed),
           "overlap": overlap}
    with io.open(Path(__file__).with_name("firing.json"), "w",
                 encoding="utf-8", newline="\n") as stream:
        json.dump(out, stream, ensure_ascii=False, indent=1)
        stream.write("\n")

    print(f"company 응답 있는 공고 {out['with_company_response']}건")
    print(f"적용 대상(발화 조건 참) {out['applicable']}건 · {out['applicable'] / 200:.1%}")
    print(f"실제 판정이 바뀐 셀     {out['changed_cells']}건 · {out['changed_cells'] / 200:.1%}")
    for row in overlap:
        print(f"  겹침 {row['id']} 라벨 {row['label']} scope {row['scope']} reason {row['reason']}")


if __name__ == "__main__":
    main()
