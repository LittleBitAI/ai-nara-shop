"""규칙 하나씩만 켠 재생으로 항목별 기여를 잰다. 모델을 부르지 않는다.

왜 필요한가. 전체 차이만으로는 어느 규칙이 얼마를 벌었는지 말할 수 없다.
네 규칙이 서로 다른 항목만 건드리므로 단독 기여의 합이 전체 차이와 같아야 하고,
그 등식이 깨지면 규칙이 서로 간섭한다는 뜻이다.

기준은 후보 없이 HEAD 코드로 돌린 재생이다. 보관 회차의 CSV를 기준으로 쓰면
그 뒤 병합된 후처리 효과가 섞인다.
"""

import argparse
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "reports/runs/colab-1789655036303880754/dev-debug"
OUT = ROOT / "reports/team-d/final/contributions.json"
CANDIDATE = ROOT / "experiments/qualification_candidate.py"

# 규칙 하나만 켜는 임시 후보. v3는 `ITEMS` 밖에서 도는 하향 규칙이라 켜는 방식이 다르다.
STUB = '''"""기여 측정용 임시 후보. 규칙 하나만 켠다."""
import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location("cand", r"{candidate}")
cand = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cand)
if "{item}" == "v3":
    cand.ITEMS = ()
else:
    cand.ITEMS = ("{item}",)
    cand.performance_below_budget = lambda _rec: None


def postprocess(judgment, rec):
    return cand.postprocess(judgment, rec)
'''


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def head_short():
    done = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"],
                          capture_output=True, text=True)
    return done.stdout.strip() if done.returncode == 0 else None


def macro_f1(replay_run, script, candidate_module, work):
    """후보 하나를 재생하고 채점해 Macro F1만 돌려준다.

    채점은 `tools/score.py`를 그대로 띄운다. 그 진입점이 인자를 받지 않으므로
    같은 프로세스에서 부르면 이 도구의 인자를 읽어 버린다.
    """
    result = replay_run.replay(script, CASE, input_path=ROOT / "open/dev.jsonl",
                               data_dir=ROOT / "open/data",
                               postprocess=getattr(candidate_module, "postprocess", None))
    work.mkdir(parents=True, exist_ok=True)
    produced = work / "submission.csv"
    produced.write_bytes(replay_run.to_csv_bytes(script, result["rows"]))
    out = work / "score"
    done = subprocess.run([sys.executable, "-X", "utf8", str(ROOT / "tools/score.py"),
                           "--truth", str(ROOT / "open/dev_labels.csv"),
                           "--pred", str(produced), "--output-dir", str(out)],
                          capture_output=True, text=True)
    if done.returncode != 0:
        raise ValueError(f"채점 실패: {done.stderr.strip()}")
    return json.loads((out / "metrics.json").read_text(encoding="utf-8"))["macro_f1"]


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure:
            reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--items", default="v8,v7,v4,v3")
    args = parser.parse_args(argv)
    items = [i.strip() for i in args.items.split(",") if i.strip()]

    replay_run = load(ROOT / "tools/replay_run.py", "replay_run")
    script = load(ROOT / "script.py", "submission")
    head = head_short()

    with tempfile.TemporaryDirectory(prefix="team-d-contrib-") as tmp:
        tmp = Path(tmp)
        baseline = macro_f1(replay_run, script, None, tmp / "base")
        per_rule = {}
        for item in items:
            stub = tmp / f"only_{item}.py"
            stub.write_text(STUB.format(candidate=CANDIDATE, item=item),
                            encoding="utf-8", newline="\n")
            per_rule[item] = macro_f1(replay_run, script,
                                      load(stub, f"only_{item}"), tmp / item)
        every = macro_f1(replay_run, script, load(CANDIDATE, "candidate"), tmp / "all")

    record = {
        "purpose": "per_rule_contribution", "model_called": False,
        "note": "같은 보관 원응답을 HEAD 코드로 재생하며 규칙을 하나씩만 켠 결과다. 새 모델 실행이 아니다.",
        "case": script.record_path(str(CASE)), "head": head,
        "baseline_macro_f1": baseline, "all_rules_macro_f1": every,
        "per_rule": {k: {"macro_f1": v, "delta": round(v - baseline, 12)}
                     for k, v in per_rule.items()},
        "sum_of_deltas": round(sum(v - baseline for v in per_rule.values()), 12),
        "observed_total_delta": round(every - baseline, 12),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n",
                   encoding="utf-8", newline="\n")
    for name, value in record["per_rule"].items():
        print(f"{name} {value['delta']:+.6f}")
    print(f"합계 {record['sum_of_deltas']:+.6f} · 실측 {record['observed_total_delta']:+.6f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
