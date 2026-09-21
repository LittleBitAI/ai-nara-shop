"""`reports/measurements.json` 을 근거 파일에서 통째로 다시 만든다. 모델을 안 부른다.

**숫자를 손으로 옮기지 않는다.** 각 행의 `macro_f1` 은 `evidence` 가 가리키는
`metrics.json` 에서 읽고, 그 대조는 `tools/measurements.py --check` 가 매번 다시 한다.
장부는 생성물이므로 고칠 일이 생기면 이 파일을 고치고 다시 돌린다 — 장부를 손으로 안 고친다.

  python -X utf8 tools/build_measurements.py
  python -X utf8 tools/measurements.py --check
"""

import argparse
import glob
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "reports" / "measurements.json"
BASELINE = "기준 0.593846165415"        # dev-debug HEAD 재생. cpu-replay 행이 공유하는 기준


def macro(rel):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))["macro_f1"]


def run_date(run):
    """회차 manifest 의 시각. 없으면 첫 회차 날짜로 둔다 — 추정하지 않고 고정값을 쓴다."""
    path = ROOT / "reports/runs" / run / "manifest.json"
    if path.is_file():
        entry = json.loads(path.read_text(encoding="utf-8"))
        for key in ("created_at", "registered_at", "run_started_at"):
            if entry.get(key):
                return str(entry[key])[:10]
    return "2026-09-17"


def run_commits():
    """`docs/runs.md` 색인이 회차별 코드 커밋을 소유한다. 여기서 다시 적지 않는다."""
    found = {}
    for line in (ROOT / "docs/runs.md").read_text(encoding="utf-8").splitlines():
        hit = re.match(r"\|\s*`(colab-\d+)`\s*\|\s*`?([0-9a-f]{7,})`?\s*\|", line)
        if hit:
            found[hit.group(1)] = hit.group(2)
    return found


def collect():
    rows, commits = [], run_commits()

    def add(**row):
        if row.get("evidence"):
            row["macro_f1"] = macro(row["evidence"])
        rows.append(row)

    # 1) 제출 파이프라인을 통째로 GPU 로 돌린 회차
    for path in sorted(glob.glob(str(ROOT / "reports/runs/colab-*/score/metrics.json"))):
        run = Path(path).parent.parent.name
        add(id=run, date=run_date(run), kind="gpu-run", code=commits.get(run, "—"),
            evidence=f"reports/runs/{run}/score/metrics.json", note="제출 파이프라인 dev 200건")

    # 2) 일부 단계만 GPU 로 돌린 파일럿. 회차 하나가 (군 × 소비자) 만큼의 측정을 낸다
    for path in sorted(glob.glob(str(ROOT / "reports/runs/*/pilot/*/*/*-score/metrics.json"))):
        parts = Path(path).relative_to(ROOT / "reports/runs").parts
        run, arm, consumer = parts[0], parts[3], parts[4].removesuffix("-score")
        add(id=f"{run}/{arm}/{consumer}", date=run_date(run), kind="gpu-pilot",
            code=commits.get(run, "1735330"),
            evidence=Path(path).relative_to(ROOT).as_posix(),
            note=f"company_size {arm} 군 · 소비자 {consumer} · 혼합 CPU 재생")

    # 3) 모델을 안 부르고 후처리만 바꾼 측정. 같은 원응답이라 회차 churn 이 없다
    for rid, code, rel, note in (
        ("a4-scope-gate", "c81644d", "reports/team-c/a4-scope-gate/candidate-score/metrics.json",
         f"A4 v6·v9·v23 게이트 · PR #69 · {BASELINE}"),
        ("a5-head-baseline", "734b4ec", "reports/team-c/a5-label-definition/head-score/metrics.json",
         "A5 가 쓴 HEAD 재생 기준 (astra) · PR #71"),
        ("a5-h2-absence", "734b4ec", "reports/team-c/a5-label-definition/absence-score/metrics.json",
         f"A5 H2 v11 부재 연결 (astra) · PR #71 · {BASELINE}"),
        ("a4-a5-combined", "ae79d50", "reports/team-c/a4-a5-combined/combined-score/metrics.json",
         f"A4 + A5 H2 합본 · PR #75 · {BASELINE}"),
    ):
        if (ROOT / rel).is_file():
            add(id=rid, date="2026-09-21", kind="cpu-replay", code=code, evidence=rel, note=note)

    # 4) 대회 서버. 근거 파일이 없다 — 사용자가 대회 화면에서 옮긴 값이다
    for entry in json.loads((ROOT / "reports/submissions.json").read_text(encoding="utf-8"))["submissions"]:
        code = (entry.get("code_commit") or "—")[:7]
        score = entry.get("leaderboard_macro_f1")
        note = (f"비공개 1,853건 · 같은 ZIP dev {entry.get('dev_macro_f1_same_zip')} · "
                f"{entry.get('elapsed_seconds')}초" if score is not None
                else f"미채점 ({entry.get('outcome')})")
        rows.append({"id": f"server/{code}", "date": entry.get("submitted_on", "2026-09-??"),
                     "kind": "server", "code": code, "macro_f1": score, "evidence": None, "note": note})
    return rows


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure:
            reconfigure(encoding="utf-8")   # 파이프에 붙은 파이썬은 로케일 인코딩으로 죽는다
    argparse.ArgumentParser(description=__doc__).parse_args(argv)
    rows = collect()
    payload = {
        "owner": "이 파일은 생성물이다. tools/build_measurements.py 가 만들고 손으로 고치지 않는다. "
                 "수치는 evidence 의 metrics.json 에서 그대로 읽었다.",
        "verify": "python -X utf8 tools/measurements.py --check",
        "rebuild": "python -X utf8 tools/build_measurements.py",
        "kinds": {
            "gpu-run": "제출 파이프라인 전체를 GPU 로 돌린 회차. dev 200건",
            "gpu-pilot": "일부 단계만 GPU 로 돌리고 나머지는 보관 원응답으로 재생한 회차. "
                         "전체 GPU 점수가 아니다",
            "cpu-replay": "모델을 안 부르고 보관 원응답으로 후처리만 바꾼 측정. 회차 churn 이 없다",
            "server": "대회 서버 채점. 입력이 dev 200건이 아니라 비공개 1,853건이다",
        },
        "caveats": [
            "kind 가 다른 행을 같은 저울로 비교하지 않는다.",
            "같은 코드의 회차 간 churn 이 4,800셀 중 29~45개이고 그 Macro F1 영향이 "
            "0.000008~0.004689다.",
            "cpu-replay 는 같은 원응답을 쓰므로 churn 이 없다. 프롬프트가 바뀌면 다시 재야 한다.",
            "server 행에는 evidence 파일이 없다. 사용자가 대회 화면에서 옮긴 값이다.",
        ],
        "measurements": rows,
    }
    LEDGER.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                      encoding="utf-8", newline="\n")
    kinds = {}
    for row in rows:
        kinds[row["kind"]] = kinds.get(row["kind"], 0) + 1
    print(f"{LEDGER.relative_to(ROOT).as_posix()} · {len(rows)}행 · {kinds}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
