"""오류 공고의 세부품명번호를 제공 고시 CSV 에서 정확히 조회한다. 모델을 안 부른다.

`README.md` §4 의 정정 표를 내는 스크립트다. 이 조회가 결론 하나를 뒤집었다 —
`PPS-DEV-23` 의 품번은 **고시에 있다**(드론). 그 공고가 중기간 경쟁입찰에서 빠진 것은
품목 때문이 아니라 시행령 제7조제1항제4호의 법정 예외 때문이고, 그래서 품번 축(C9)이
아니라 조문 축(C11)이 닫는다.

**`load_sme_reference()` 를 먼저 부르는 것이 이 스크립트의 요점이다.** 안 부르면
`_PRODUCTS` 가 비어 `competitive_product()` 가 전부 `None` 을 낸다 — 품번이 고시에
없다는 뜻이 아니라 **조회를 못 했다는 뜻**인데, 그 둘을 헷갈리면 잘못된 결론이 나온다.
실제로 한 번 그렇게 틀렸다.

    py -X utf8 reports/team-c/v10-v11-v13-breakdown/catalogue_lookup.py

기준 커밋의 `script.py` 를 임시 폴더에 풀어 쓴다. 작업 트리 판을 쓰지 않는다.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BASE_REV = "772ca12"
DATA = "open/data"
CATALOGUE = ROOT / "open/data/법령패키지/중기부고시/중기부고시_경쟁제품_세부품명.csv"
# 세부품명번호는 10자리. 운영 `sme_product_lookup()` 과 같은 패턴을 쓴다.
CODE = re.compile(r"(?<!\d)\d{10}(?!\d)")
# §2 의 오류 셀이 있는 공고. v10·v11·v13 의 FP·FN 을 낸 자리 전부.
NOTICES = ("PPS-DEV-13", "PPS-DEV-23", "PPS-DEV-039", "PPS-DEV-040", "PPS-DEV-069",
           "PPS-DEV-075", "PPS-DEV-128", "PPS-DEV-060", "PPS-DEV-143", "PPS-DEV-03",
           "PPS-DEV-056", "PPS-DEV-076", "PPS-DEV-193")


def pinned_script():
    source = subprocess.run(["git", "-C", str(ROOT), "show", f"{BASE_REV}:script.py"],
                            capture_output=True, check=True).stdout
    path = Path(tempfile.mkdtemp(prefix="c-catalogue-")) / "script.py"
    path.write_bytes(source)
    spec = importlib.util.spec_from_file_location("pinned_script", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dev", default=str(ROOT / "open/dev.jsonl"))
    parser.add_argument("--data", default=str(ROOT / DATA))
    args = parser.parse_args(argv)

    script = pinned_script()
    # 이 한 줄이 핵심이다. 안 부르면 아래 판정이 전부 None 이 된다.
    script.load_sme_reference(args.data)
    print(f"고시 적재 {len(script._PRODUCTS)}행 ← {CATALOGUE.relative_to(ROOT).as_posix()}")
    listed = {p["세부품명번호"]: p for p in script._PRODUCTS}

    index = {}
    with Path(args.dev).open(encoding="utf-8") as stream:
        for line in stream:
            rec = json.loads(line)
            if rec.get("id") in NOTICES:
                index[rec["id"]] = rec

    print(f"\n{'공고':16}{'품번':14}{'고시':6}{'추정가':>14}  competitive_product()")
    for key in NOTICES:
        rec = index.get(key)
        if rec is None:
            print(f"  {key:14} (레코드 없음)")
            continue
        meta = rec.get("meta") or {}
        codes = CODE.findall(str(meta.get("세부품명번호목록") or ""))
        price = script.estimated_price(rec)
        verdict = script.competitive_product(rec, set(codes)) if codes else None
        shown = ",".join(codes) if codes else "없음"
        mark = "" if not codes else ("O" if any(c in listed for c in codes) else "X")
        print(f"  {key:14}{shown:14}{mark:6}{price if price is not None else '-':>14}  {verdict}")
        for code in codes:
            row = listed.get(code)
            if row is None:
                print(f"      {code} → 고시에 **없다** — C9 의 대상이다")
                continue
            cap = script.product_cap_won(row)
            print(f"      {code} → 고시에 **있다** · {row['세부품명']} · {row['제품명']}"
                  f" · 상한 {cap}")
            if row["특이사항"]:
                print(f"          특이사항: {row['특이사항']}")

    print("\n  `None` 은 '품번이 없거나 판단 불가' 다. '고시에 없다' 가 아니다 —"
          " 그 둘을 헷갈리면 C9 의 대상을 잘못 센다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
