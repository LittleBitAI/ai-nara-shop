"""두 회차의 company_size 사실이 얼마나 달라졌나 — 34셀이 전부인지 본다.

같은 dev 200건에 같은 모델·같은 설정이고 프롬프트에 필드 하나가 늘었다.
사실이 넓게 흔들렸다면 34셀은 눈에 보인 일부일 뿐이다.

    py -X utf8 reports/team-c/b1-aftermath/fact_drift.py
"""
import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "reports/runs/colab-1789902969401579900/dev-debug"
CAND = ROOT / "reports/runs/colab-1790141677344456786/dev-debug"
FIELDS = ("scope", "qualification", "qualification_role", "qualification_complete",
          "priority_exception", "size_exception", "requirements_complete",
          "software_business", "software_participation")


def facts(case, script):
    out = {}
    for line in (case / "diagnostics.jsonl").read_text(encoding="utf-8").splitlines():
        e = json.loads(line)
        if (e.get("event") == "response" and e.get("status") == "valid"
                and e.get("phase") == "company_size" and "response_text" in e):
            obj = script.extract_json(e["response_text"])
            f = (obj.get("company_size") if isinstance(obj, dict) else None) or {}
            out[e["id"]] = f
    return out


def main():
    spec = importlib.util.spec_from_file_location("submission", ROOT / "script.py")
    script = importlib.util.module_from_spec(spec)
    sys.modules["submission"] = script
    spec.loader.exec_module(script)

    a, b = facts(BASE, script), facts(CAND, script)
    shared = sorted(set(a) & set(b))
    print(f"두 회차 모두 유효 응답이 있는 공고: {len(shared)}건\n")

    per_field = Counter()
    moved = []
    for i in shared:
        diff = [k for k in FIELDS if a[i].get(k) != b[i].get(k)]
        if diff:
            moved.append(i)
            per_field.update(diff)
    print(f"사실이 하나라도 달라진 공고: {len(moved)}건 / {len(shared)} "
          f"({len(moved) / len(shared):.0%})\n")
    print(f'{"필드":<26}{"달라진 공고 수":>14}')
    for k in FIELDS:
        if per_field[k]:
            print(f"  {k:<24}{per_field[k]:>12}")
    print()
    print("인용 필드(값이 길어 따로 센다)")
    for k in ("scope_quote", "qualification_quote", "priority_exception_quote",
              "size_exception_quote", "direct_production_quote", "software_business_quote"):
        n = sum(1 for i in shared if a[i].get(k) != b[i].get(k))
        if n:
            print(f"  {k:<24}{n:>12}")


if __name__ == "__main__":
    main()
