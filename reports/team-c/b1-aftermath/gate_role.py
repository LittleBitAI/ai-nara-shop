"""바뀐 셀에 competitive_row 게이트가 실제로 관여했는가.

게이트는 `scope=="competitive"` 이고 지목한 행이 제공 목록 **밖**일 때만 scope 를
`unknown` 으로 만든다. 그 조건이 성립한 공고를 센다.

    py -X utf8 reports/team-c/b1-aftermath/gate_role.py
"""
import csv
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CAND = ROOT / "reports/runs/colab-1790141677344456786/dev-debug"


def main():
    spec = importlib.util.spec_from_file_location("submission", ROOT / "script.py")
    script = importlib.util.module_from_spec(spec)
    sys.modules["submission"] = script
    spec.loader.exec_module(script)
    script.load_sme_reference(str(ROOT / "open/data"))

    texts, chars = {}, {}
    for line in (CAND / "diagnostics.jsonl").read_text(encoding="utf-8").splitlines():
        e = json.loads(line)
        if e.get("event") == "company_size_input":
            chars[e["id"]] = e["max_chars"]
        if (e.get("event") == "response" and e.get("status") == "valid"
                and e.get("phase") == "company_size" and "response_text" in e):
            texts[e["id"]] = e["response_text"]

    fired, competitive, with_row, outside = [], 0, 0, []
    for rec in script.iter_records(str(ROOT / "open/dev.jsonl")):
        text = texts.get(rec["id"])
        if not text:
            continue
        obj = script.extract_json(text)
        facts = (obj.get("company_size") if isinstance(obj, dict) else None) or {}
        if facts.get("scope") != "competitive":
            continue
        competitive += 1
        row = facts.get("competitive_row")
        visible = script.build_context(rec, chars[rec["id"]])
        lookup = script.sme_product_lookup(rec, visible, script._PRODUCTS)
        supplied = {p["세부품명번호"] for p in lookup.get("일치후보") or ()}
        supplied |= {r[0] for r in lookup.get("서비스보조목록") or ()}
        if row:
            with_row += 1
            if row not in supplied:
                outside.append((rec["id"], row))
                fired.append(rec["id"])
        else:
            fired.append(rec["id"])          # null → 게이트 발동

    print(f"scope=competitive                : {competitive}건")
    print(f"  competitive_row 있음           : {with_row}건")
    print(f"    그중 제공 목록 밖(지어냄)    : {len(outside)}건 {outside}")
    print(f"  competitive_row = null         : {competitive - with_row}건")
    print(f"게이트가 scope 를 unknown 으로 만든 공고: {len(fired)}건")
    print(f"  {sorted(x.replace('PPS-DEV-', '') for x in fired)}")

    base = {r["id"]: r for r in csv.DictReader(open(sys.argv[1], encoding="utf-8"))}
    cand = {r["id"]: r for r in csv.DictReader(open(CAND / "submission.csv", encoding="utf-8"))}
    changed = {i for i in base for v in script.ITEMS if base[i][v] != cand[i][v]}
    both = sorted(set(fired) & changed)
    print()
    print(f"바뀐 셀이 있는 공고            : {len(changed)}건")
    print(f"그중 게이트가 발동한 공고      : {len(both)}건 "
          f"{[x.replace('PPS-DEV-', '') for x in both]}")
    print()
    if not both:
        print("★ 바뀐 셀 어디에도 게이트가 관여하지 않았다.")
        print("  즉 34셀은 competitive_row 게이트가 아니라 **같은 프롬프트로 다시 부른")
        print("  모델의 응답 차이**에서 나왔다. 회차 간 변동과 프롬프트 변경 효과가 섞여 있고")
        print("  이 회차 하나로는 둘을 못 가른다.")


if __name__ == "__main__":
    main()
