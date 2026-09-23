"""C5 — v11 의 양성 5건(TP 2 · FP 3)과 FN 4건이 **어느 경로에서 정해졌는지** 분해한다.

v11 은 C 항목 중 유일하게 **FN 이 FP 보다 크다**(2/3/4). 그래서 "무엇이 올렸나" 만 보면
절반을 놓친다 — **무엇이 못 올렸나**를 같이 센다.

v11 을 쓸 수 있는 자리는 운영 코드에 둘뿐이다.
  1. **앞 단계 보존** — baseline(+SME 재검증)이 남긴 1 을 아무도 안 덮는다
  2. **경쟁제품 게이트** — 후처리 `apply_competitive_rules()` 가 1 을 올린다.
     조건 셋이 다 참이어야 한다 — 직생 요구 문장 있음 · 카탈로그 대조 `True` ·
     `SME_ALLOWED` 정규식이 원문에서 **안** 걸림(부재탐지라 "없어야" 위반이다)

게이트가 못 올린 공고는 **셋 중 어느 조건에서 막혔는지**까지 적는다. 그것이 FN 의 주소다.

**이 스크립트는 분해와 집계까지다. 규칙을 만들지 않는다.**

    py -X utf8 reports/team-c/c5-v11-paths/paths.py

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
ITEM = "v11"


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


def gate_trace(script, rec):
    """게이트의 조건 셋을 그대로 다시 밟는다. 판정이 아니라 **어디서 멈췄나**를 낸다."""
    quote, codes = script.direct_production_demand(rec)
    if quote is None:
        return {"직생요구": False, "카탈로그": None, "중소허용": None, "막힌곳": "직생 요구 없음"}
    listed = script.competitive_product(rec, codes)
    visible = script.build_context(rec, max_chars=script.PROMPT_BUDGET)
    allowed = bool(script.SME_ALLOWED.search(visible))
    if listed is not True:
        where = "카탈로그 불일치" if listed is False else "카탈로그 미확인"
        return {"직생요구": True, "카탈로그": listed, "중소허용": allowed, "막힌곳": where}
    if allowed:
        return {"직생요구": True, "카탈로그": True, "중소허용": True, "막힌곳": "중소 허용 문구 있음"}
    return {"직생요구": True, "카탈로그": True, "중소허용": False, "막힌곳": None}


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

    rows, tally = [], {}
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
        if company_text is not None:
            focused, _ = script.parse_judgment(company_text,
                                               expected_items=script.COMPANY_SIZE_KEYS, **legacy)
            verified, _reason = script.verify_company_size(focused["company_size"], rec,
                                                           chars[identifier])
            parsed.update(verified)
        before = int((parsed.get(ITEM) or {}).get("위반여부", 0))
        final = int(script.postprocess(parsed, rec)[ITEM]["위반여부"])
        label = int(truth[identifier][ITEM])
        trace = gate_trace(script, rec)

        key = f'{"게이트 통과" if trace["막힌곳"] is None else trace["막힌곳"]} · 앞단계={before} · 라벨={label}'
        tally[key] = tally.get(key, 0) + 1

        if final == 1 or label == 1:
            rows.append({
                "id": identifier.replace("PPS-DEV-", ""),
                "라벨": label, "최종": final,
                "판정": "TP" if final == label == 1 else ("FP" if final == 1 else "FN"),
                "경로": ("게이트" if trace["막힌곳"] is None and before == 0
                       else "앞 단계 보존" if before == 1 else "—"),
                "앞단계": before, **trace,
            })

    payload = {"item": ITEM, "dev_n": 200, "cells": rows,
               "gate_tally": dict(sorted(tally.items()))}
    with io.open(Path(__file__).with_name("paths.json"), "w",
                 encoding="utf-8", newline="\n") as stream:
        json.dump(payload, stream, ensure_ascii=False, indent=1)
        stream.write("\n")

    print(f'{"공고":<6}{"판정":<5}{"경로":<14}{"앞단계":>6}{"직생":<7}{"카탈로그":<10}'
          f'{"중소허용":<9}{"막힌곳"}')
    for row in sorted(rows, key=lambda r: (r["판정"], r["id"])):
        print(f'{row["id"]:<6}{row["판정"]:<5}{row["경로"]:<14}{row["앞단계"]:>6}'
              f'{str(row["직생요구"]):<7}{str(row["카탈로그"]):<10}'
              f'{str(row["중소허용"]):<9}{row["막힌곳"] or "(통과)"}')

    print(f'\n{"판정":<6}{"n":>4}')
    for verdict in ("TP", "FP", "FN"):
        print(f'{verdict:<6}{sum(r["판정"] == verdict for r in rows):>4}')

    print(f'\n게이트 동작 전수 {payload["dev_n"]}건')
    for key, count in payload["gate_tally"].items():
        print(f'  {key:<48}{count:>4}')


if __name__ == "__main__":
    main()
