"""측정 장부를 읽어 추이 표를 찍는다. 모델을 부르지 않고 새 수치를 만들지 않는다.

장부는 `reports/measurements.json` 하나다. 이 도구는 그것을 렌더할 뿐이고,
각 행의 `macro_f1`이 실제로 그 `evidence` 경로의 `metrics.json`과 같은지 검사한다.
손으로 적은 숫자가 근거와 어긋나면 종료 코드가 0이 아니다 — 추이표가 조용히 틀리는 것을 막는다.

  python -X utf8 tools/measurements.py            # 검사하고 표를 찍는다
  python -X utf8 tools/measurements.py --check    # 검사만 한다
"""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "reports" / "measurements.json"
TOLERANCE = 5e-13  # 부동소수점 왕복만 허용한다. 반올림해 적은 값은 통과시키지 않는다


def load():
    return json.loads(LEDGER.read_text(encoding="utf-8"))


def verify(rows):
    """각 행의 macro_f1을 근거 파일에서 다시 읽어 대조한다. 어긋난 행 목록을 돌려준다."""
    bad = []
    for row in rows:
        evidence = row.get("evidence")
        if not evidence:
            continue                      # 근거 파일이 없는 행(서버 점수 등)은 대조 대상이 아니다
        path = ROOT / evidence
        if not path.is_file():
            bad.append((row["id"], f"근거 파일이 없다: {evidence}"))
            continue
        actual = json.loads(path.read_text(encoding="utf-8")).get("macro_f1")
        claimed = row.get("macro_f1")
        if actual is None or claimed is None or abs(actual - claimed) > TOLERANCE:
            bad.append((row["id"], f"장부 {claimed} != 근거 {actual}"))
    return bad


def render(rows):
    print(f"{'날짜':10} {'종류':10} {'측정':42} {'코드':9} {'Macro F1':>16}  비고")
    print("-" * 140)
    for row in sorted(rows, key=lambda r: (r["date"], r["kind"], r["id"])):
        f1 = row.get("macro_f1")
        shown = f"{f1:.12f}" if isinstance(f1, (int, float)) else "미채점"
        print(f"{row['date']:10} {row['kind']:10} {row['id'][:42]:42} {row.get('code','—')[:9]:9} "
              f"{shown:>16}  {row.get('note','')[:52]}")


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure:
            reconfigure(encoding="utf-8")   # 파이프에 붙은 파이썬은 로케일 인코딩으로 죽는다
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="표를 찍지 않고 대조만 한다")
    args = parser.parse_args(argv)

    rows = load()["measurements"]
    bad = verify(rows)
    if not args.check:
        render(rows)
    if bad:
        print("\n장부와 근거가 어긋난다:", file=sys.stderr)
        for rid, why in bad:
            print(f"  {rid}: {why}", file=sys.stderr)
        return 1
    print(f"\n{len(rows)}행 · 근거 대조 통과")
    return 0


def demo():
    """근거와 어긋난 값을 검사가 실제로 잡는지 본다."""
    rows = load()["measurements"]
    assert verify(rows) == [], "현재 장부가 이미 어긋나 있다"
    victim = next(r for r in rows if r.get("evidence"))
    tampered = [dict(r, macro_f1=r["macro_f1"] + 1e-6) if r is victim else r for r in rows]
    assert verify(tampered), "값을 흔들었는데 검사가 못 잡았다"
    missing = [dict(r, evidence="reports/없는파일.json") if r is victim else r for r in rows]
    assert verify(missing), "근거 파일이 없는데 검사가 못 잡았다"
    print("measurements self-check passed")


if __name__ == "__main__":
    raise SystemExit(demo() if "--demo" in sys.argv else main())
