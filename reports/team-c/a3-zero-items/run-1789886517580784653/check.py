"""실제 저장 CSV로 옛 검사 실패와 공용/A3 검사 수정을 재현한다. 모델 호출 없음."""

import csv
import hashlib
import json
from pathlib import Path
import subprocess
import textwrap

ROOT = Path(__file__).resolve().parents[4]
RUN = ROOT / "reports/runs/colab-1789886517580784653"
OLD = "13041f5b72618dda38bd852bf8ed71b7155b7e4a"


def csv_check(raw):
    notebook = json.loads(raw)
    source = next("".join(c["source"]) for c in notebook["cells"] if c["id"] == "sample")
    # 실제 check_live의 CSV 검사 구간만 실행한다. GPU/ZIP 동일성 검증과 구분한다.
    return textwrap.dedent(source[source.index('    columns = ["id"]'):
                                  source.index('    with zipfile.ZipFile(WORK / "submit.zip")')])


def main():
    report = json.loads((RUN / "dev/run_report.json").read_text(encoding="utf-8"))
    script_bytes = subprocess.check_output(["git", "show", "b7ac265:script.py"], cwd=ROOT)
    assert hashlib.sha256(script_bytes).hexdigest() == report["code_sha256"]
    assert report["mode"] == "live" and report["model_success_count"] == 200
    result = {"mode": "saved_csv_gate_check", "model_called": False, "old_reproduced": False,
              "notebooks": {}}
    old = subprocess.check_output(["git", "show", f"{OLD}:notebooks/exp-a3-source-role.ipynb"], cwd=ROOT)
    sources = {"old": old, **{name: (ROOT / "notebooks" / name).read_bytes()
                             for name in ("colab-baseline.ipynb", "exp-a3-source-role.ipynb")}}
    for name, raw in sources.items():
        namespace = dict(json=json, csv=csv, RESULTS=RUN.parent, name=RUN.name + "/dev",
                         report=report, settings=report["reproduction"]["settings"], expected=200)
        try:
            exec(compile(csv_check(raw), name, "exec"), namespace)
        except RuntimeError as exc:
            assert name == "old" and str(exc) == "추가 분석을 생략한 공고가 변경됐습니다."
            result["old_reproduced"] = True
        else:
            assert name != "old", "옛 검사의 실제 실패가 재현되지 않았다"
            result["notebooks"][name] = "saved_csv_checks_pass"
    assert result["old_reproduced"]
    output = Path(__file__).with_name("gate-check.json")
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                      encoding="utf-8", newline="\n")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
