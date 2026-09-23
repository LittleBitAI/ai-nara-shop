"""지목된 행의 조건이 이 공고의 구매 대상과 맞는가 — 제공 고시 자료만 쓴다.

B1 회차가 가리킨 방향의 근거를 만든다. 후보 코드나 프롬프트를 만들지 않는다.
대조표만 낸다. 카탈로그·금액 함수는 후보 회차 코드(`9ed0805`)의 것을 쓴다(pin.py).

    py -X utf8 reports/team-c/b1-aftermath/row_conditions.py
"""
import csv
import io
import json
import re

from pin import CAND_REV, ROOT, load_script

CAND = ROOT / "reports/runs/colab-1790141677344456786/dev-debug"
SCOPE_ITEMS = ("v10", "v11", "v12", "v13")


def main():
    script = load_script(CAND_REV)
    rows = {p["세부품명번호"]: p for p in script._PRODUCTS}

    texts, chars = {}, {}
    for line in (CAND / "diagnostics.jsonl").read_text(encoding="utf-8").splitlines():
        e = json.loads(line)
        if e.get("event") == "company_size_input":
            chars[e["id"]] = e["max_chars"]
        if (e.get("event") == "response" and e.get("status") == "valid"
                and e.get("phase") == "company_size" and "response_text" in e):
            texts[e["id"]] = e["response_text"]

    truth = {r["id"]: r for r in csv.DictReader(open(ROOT / "open/dev_labels.csv", encoding="utf-8"))}
    cand = {r["id"]: r for r in csv.DictReader(open(CAND / "submission.csv", encoding="utf-8"))}

    # 사정권 4건 + 현재 v10~v13 TP 를 내는 공고
    reach = {"PPS-DEV-039", "PPS-DEV-040", "PPS-DEV-041", "PPS-DEV-044"}
    tp = {i for i in truth for v in SCOPE_ITEMS if truth[i][v] == "1" and cand[i][v] == "1"}
    want = reach | tp

    print(f"사정권 {len(reach)}건 · 현재 v10~v13 TP 공고 {len(tp)}건 (겹침 {len(reach & tp)})\n")
    out = []
    for rec in script.iter_records(str(ROOT / "open/dev.jsonl")):
        i = rec["id"]
        if i not in want:
            continue
        text = texts.get(i)
        obj = script.extract_json(text) if text else None
        facts = (obj.get("company_size") if isinstance(obj, dict) else None) or {}
        row_no = facts.get("competitive_row")
        row = rows.get(row_no) if row_no else None
        price = script.estimated_price(rec)
        cap = script.product_cap_won(row) if row else None
        meta = rec.get("meta", {}) or {}
        notice = "\n".join(d["text"] for d in rec["docs"])
        flat = re.sub(r"\s+", "", notice)
        name = re.sub(r"\s+", "", row["세부품명"]) if row else ""
        out.append({
            "id": i.replace("PPS-DEV-", ""),
            "group": "사정권" if i in reach else "TP",
            "scope": facts.get("scope"),
            "row": row_no,
            "품명": row["세부품명"] if row else None,
            "특이사항": (row.get("특이사항") or "").strip() if row else None,
            "상한": cap,
            "추정가격": price,
            "상한초과": (cap is not None and price is not None and price >= cap) if cap else None,
            "품명이 원문에": (name in flat) if name else None,
            "메타품목": meta.get("세부품명번호목록"),
            "라벨": {v: truth[i][v] for v in SCOPE_ITEMS if truth[i][v] == "1"},
        })
    # 줄끝을 LF 로 고정한다. 기본값으로 열면 윈도에서 CRLF 로 나간다.
    with io.open(ROOT / "reports/team-c/b1-aftermath/row-conditions.json", "w",
                 encoding="utf-8", newline="\n") as stream:
        json.dump(out, stream, ensure_ascii=False, indent=1)
        stream.write("\n")

    print(f'{"공고":<6}{"군":<7}{"scope":<13}{"지목 행":<12}{"품명":<22}'
          f'{"상한":>13}{"추정가격":>14}{"초과":<6}{"품명 원문":<10}라벨')
    for r in sorted(out, key=lambda x: (x["group"], x["id"])):
        print(f'{r["id"]:<6}{r["group"]:<7}{str(r["scope"]):<13}{str(r["row"]):<12}'
              f'{str(r["품명"])[:20]:<22}{("-" if r["상한"] is None else f"{r[chr(49)+chr(48)]:,}") if False else (f"{r["상한"]:,}" if r["상한"] else "-"):>13}'
              f'{(f"{r["추정가격"]:,.0f}" if r["추정가격"] else "-"):>14}'
              f'{str(r["상한초과"]):<6}{str(r["품명이 원문에"]):<10}{",".join(r["라벨"]) or "-"}')


if __name__ == "__main__":
    main()
