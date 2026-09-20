"""H2 보호 범위·구 원응답 재생 검사. 실제 모델 성능 측정이 아니다."""

import ast
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
import script  # noqa: E402
from tools import replay_run  # noqa: E402


def main():
    before = subprocess.check_output(["git", "show", "6738328:script.py"], cwd=ROOT)
    after = (ROOT / "script.py").read_bytes()
    trees = [ast.parse(source.decode("utf-8")) for source in (before, after)]
    allowed = {"extra_call_items", "company_size_schema", "empty_company_size", "verify_company_size",
               "verify_document_requirements", "parse_judgment", "run", "_run"}
    functions = [{n.name: ast.dump(n) for n in tree.body if isinstance(n, ast.FunctionDef)} for tree in trees]
    assert all(functions[0].get(k) == functions[1].get(k) for k in functions[0].keys() | functions[1].keys()
               if k not in allowed), "허용 범위 밖 함수 변경"
    for name in ("_company_size_bands", "company_size_products"):
        assert functions[0][name] == functions[1][name]
    assert not script.SPLIT_ITEMS and not script.PRODUCT_ITEMS
    assert "PPS-DEV" not in script.COMPANY_SIZE_PROMPT
    replay_checks = []
    with tempfile.TemporaryDirectory() as temporary:
        path = Path(temporary) / "baseline.py"
        path.write_bytes(before)
        baseline = replay_run.load_module(path, "a3_h2_baseline")
        for case in ("colab-1789880471715651259", "colab-1789889904147841755"):
            source = ROOT / "reports/runs" / case / "dev-debug"
            results = [replay_run.replay(module, source, input_path=ROOT / "open/dev.jsonl",
                                         data_dir=ROOT / "open/data") for module in (baseline, script)]
            csvs = [replay_run.to_csv_bytes(script, result["rows"]) for result in results]
            assert csvs[0] == csvs[1], f"옛 원응답의 CSV 변경: {case}"
            replay_checks.append({"case": f"reports/runs/{case}/dev-debug", "rows": len(results[0]["rows"]),
                                  "csv_bytes_identical": True, "changed_cells": 0,
                                  "csv_sha256": hashlib.sha256(csvs[1]).hexdigest()})
    laws = ("중소기업제품 구매촉진 및 판로지원에 관한 법률.txt",
            "중소기업제품 구매촉진 및 판로지원에 관한 법률 시행령.txt",
            "소프트웨어 진흥법.txt", "중소 소프트웨어사업자의 사업 참여 지원에 관한 지침.txt")
    sources = {f"open/data/법령패키지/법령/{name}":
               hashlib.sha256((ROOT / "open/data/법령패키지/법령" / name).read_bytes()).hexdigest()
               for name in laws}
    result = {"status": "cpu_contracts_only", "model_called": False, "base_commit": "6738328",
              "script_sha256": hashlib.sha256(after).hexdigest(), "protected_functions_unchanged": True,
              "old_response_replays": replay_checks, "source_sha256": sources,
              "extra_call_items": script.extra_call_items(),
              "live_target_tp": None, "same_zip_churn": None, "unlabeled_firing_rates": None,
              "server_time": None}
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
