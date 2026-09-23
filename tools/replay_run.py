"""보관된 원응답으로 판정 후단계를 GPU 없이 다시 돌린다. 모델을 부르지 않는다.

`postprocess`·`verify_sme`처럼 모델 뒤에 오는 단계만 바꾸는 후보는 이것으로 잰다.
프롬프트·스키마를 바꾸는 후보는 저장된 응답이 달라지므로 Colab 회차가 필요하다.
"""

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    # 후보가 저장소 루트의 script.py 를 따로 읽지 않고 여기서 읽은 것을 집게 한다.
    # --script 로 다른 코드를 넘겼을 때 파싱과 postprocess 가 갈라지는 것을 막는다.
    previous = sys.modules.get(name)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        # main() 은 한 프로세스에서 여러 번 돈다. 실패한 적재가 앞 회차의 멀쩡한
        # 등록본까지 지우면 후보가 조용히 워킹트리 script.py 로 되돌아간다.
        if previous is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = previous
        raise
    return module


def run_script(case_dir, into):
    """회차가 실제로 돌린 커밋의 script.py. HEAD의 후처리가 바뀌어도 회차 재현을 확인할 수 있다."""
    manifest = Path(case_dir).resolve().parent / "manifest.json"
    if not manifest.is_file():
        raise ValueError(f"{manifest} 가 없다. --script로 회차 코드를 직접 준다")
    commit = json.loads(manifest.read_text(encoding="utf-8"))["code"]["commit"]
    shown = subprocess.run(["git", "-C", str(ROOT), "show", f"{commit}:script.py"],
                           capture_output=True)
    if shown.returncode != 0:
        raise ValueError(f"회차 커밋 {commit[:7]}의 script.py를 git에서 읽지 못했다. "
                         "전체 이력을 받거나 --script로 준다")
    path = Path(into) / f"script-{commit[:12]}.py"
    path.write_bytes(shown.stdout)
    return load_module(path, "run_submission")


def saved_responses(case_dir):
    """`--debug-responses`로 남긴 원응답. 단계별로 공고 ID에 붙여 돌려준다."""
    path = Path(case_dir) / "diagnostics.jsonl"
    if not path.is_file():
        raise ValueError(f"{path} 가 없다")
    texts = {"baseline": {}, "sme": {}}
    for line in path.read_text(encoding="utf-8").splitlines():
        event = json.loads(line)
        if event.get("event") != "response" or event.get("status") != "valid":
            continue
        if "response_text" not in event:
            raise ValueError(f"{path}: 원응답이 없다. --debug-responses로 돌린 회차가 필요하다")
        texts.setdefault(event["phase"], {})[event["id"]] = event["response_text"]
    if not texts["baseline"]:
        raise ValueError(f"{path}: 기본 단계 원응답이 없다")
    return texts


def replay(script, case_dir, *, input_path, data_dir, postprocess=None, verify_sme=None,
           verify_company_size=None):
    """저장된 응답으로 행을 다시 만든다. 바꿀 단계만 인자로 갈아 끼운다."""
    case_dir = Path(case_dir)
    report = json.loads((case_dir / "run_report.json").read_text(encoding="utf-8"))
    settings = report["reproduction"]["settings"]
    max_chars = settings["max_chars"]
    if report.get("sme_documents_shrunk"):
        # 줄어든 공고의 실제 예산은 토크나이저가 정했고 로그에 건별 값이 없다.
        raise ValueError("이 회차는 문서 예산이 축소된 공고가 있어 재생할 수 없다")
    postprocess = postprocess or script.postprocess
    verify_sme = verify_sme or script.verify_sme
    # A1 이전 회차의 코드에는 이 함수가 없다. 그 회차에는 company_size 원응답도 없으므로
    # 아래 호출 지점에 닿지 않는다. 여기서 속성을 요구하면 그 회차의 재생이 통째로 막힌다.
    verify_company_size = verify_company_size or getattr(script, "verify_company_size", None)

    texts = saved_responses(case_dir)
    # 이 제출 코드가 모르는 단계의 원응답이 있으면 조용히 건너뛰지 않는다. 건너뛰면
    # 그 단계가 바꾼 판정이 빠진 CSV를 근거로 쓰게 된다 — 실제로 한 번 그렇게 어긋났다.
    known = {"baseline", "sme", *getattr(script, "VERDICT_PHASES", ()), "company_size"}
    unknown = sorted(name for name, by_id in texts.items() if by_id and name not in known)
    if unknown:
        raise ValueError(f"이 회차에는 {unknown} 단계 원응답이 있는데 "
                         "그 코드는 재생할 줄 모른다. 더 최신 --script 로 재생한다")
    # A1은 건별 실제 문서 예산을 저장한다. 이를 빼면 보이지 않았던 인용을 재생에서 승인하게 된다.
    company_chars = {}
    for line in (case_dir / "diagnostics.jsonl").read_text(encoding="utf-8").splitlines():
        event = json.loads(line)
        if event.get("event") == "company_size_input":
            company_chars[event["id"]] = event["max_chars"]
    if report.get("company_size_response_count", 0) != len(texts.get("company_size", {})):
        raise ValueError("기업규모 원응답 건수가 실행 기록과 다르다")
    _, products = script.load_sme_reference(str(data_dir))
    rows, baseline_rows, reasons = [], [], {}
    for rec in script.iter_records(str(input_path)):
        text = texts["baseline"].get(rec["id"])
        if text is None:
            raise ValueError(f"{rec['id']}: 저장된 기본 응답이 없다")
        parsed, _ = script.parse_judgment(text)
        baseline_rows.append(script.to_row(rec["id"], script.postprocess(parsed, rec)))
        # 판정 스키마 단계(split·product)를 회차와 같은 코드로 얹는다. 전에는 이 줄이 없어
        # N1이 켜진 회차의 재생이 회차 CSV를 재현하지 못했다(v16 13건·v18 37건).
        for phase in getattr(script, "VERDICT_PHASES", ()):
            script.merge_extra_call(parsed, rec, phase, script.extra_call_items().get(phase) or (),
                                    texts.get(phase, {}).get(rec["id"]))
        sme_text = texts["sme"].get(rec["id"])
        if sme_text is not None:
            focused, _ = script.parse_judgment(sme_text, expected_items=script.SME_ITEMS, sme=True)
            verified, rejected = verify_sme(focused, rec, products, max_chars)
            reasons[rec["id"]] = rejected
            parsed.update(verified)
        company_text = texts.get("company_size", {}).get(rec["id"])
        if company_text is not None:
            if rec["id"] not in company_chars:
                raise ValueError("기업규모 입력의 문서 예산 기록이 없다")
            # 새 live 파싱은 확장 필드를 요구한다. 보관된 구 스키마만 명시적으로 구분한다.
            legacy = ({"company_size_legacy": True}
                      if hasattr(script, "DOCUMENT_CHECK_ITEMS")
                      and not settings.get("company_size_document_checks") else {})
            if hasattr(script, "CLAUSE_QUOTE_MAX"):
                legacy["company_size_clause_quotes"] = bool(settings.get("company_size_clause_quotes"))
            if hasattr(script, "QUALIFICATION_ROLES"):
                legacy["company_size_qualification_role"] = bool(settings.get("company_size_qualification_role"))
            focused, _ = script.parse_judgment(company_text, expected_items=script.COMPANY_SIZE_KEYS,
                                               **legacy)
            verified, reason = verify_company_size(focused["company_size"], rec, company_chars[rec["id"]])
            parsed.update(verified)
            reasons.setdefault(rec["id"], {})["company_size"] = reason
        rows.append(script.to_row(rec["id"], postprocess(parsed, rec)))
    if len(rows) != report["건수"]:
        raise ValueError(f"입력 건수가 회차와 다르다: {len(rows)} != {report['건수']}")
    return {"rows": rows, "baseline_rows": baseline_rows, "rejected_conditions": reasons,
            "settings": settings}


# 보관 CSV 와 현재 소비자 사이에서 **일부러** 갈린 셀. 보관물을 다시 쓰지 않고 여기에 적는다.
# 한 벌만 둔다 — 여섯 검사가 각자 베껴 두었더니 소비자를 한 번 고칠 때마다 여섯 군데가 같이
# 터졌고, v13 수리와 근거 계약에서 실제로 두 번 그랬다. 소비자를 또 고치면 이 목록만 고친다.
#  - 세 셀: `company_size_products()` 가 검증된 인용을 요구하면서 갈렸다 (PR #84).
#  - 열여섯 셀: 근거 계약을 부재탐지·v24 밖 전 항목으로 넓히면서 갈렸다. 근거 없는 위반은
#    D4-4 의 `e` 계약(원문의 연속된 부분문자열)을 못 채우므로 내린다.
#  - 서른세 셀: v24 대조 축(A7)을 `evidence_refutes()` 에 넣으면서 갈렸다. 코드가 공고와
#    등록값의 불일치를 하나도 못 찾으면 그 양성을 내린다. `e24` 가 함께 비워진다.
#  - 여덟 셀: D7 의 적용범위 게이트가 v3·v5·v6 의 오탐 네 자리에서 값과 근거를 함께
#    비웠다. 실적 구절에 연결된 배수를 인용 안에서 읽고(v3), 계약법별 고시금액 표를
#    상한·금액이 **둘 다 확인될 때만** 반증으로 쓰고(v5), 시·군·구 제한이 아닌 인용을
#    내린다(v6).
#    v4 는 게이트를 두지 않는다 — 검출기의 미탐은 확정적 음성이 아니다.
#
# 목록은 **대조 대상마다 다르다.** 회차가 다르면 모델이 낸 근거 없는 양성도 다르므로,
# 같은 소비자로 재생해도 갈리는 셀이 달라진다. 그래서 이름에 대조 대상을 박는다.
# `reports/team-c/a5-label-definition/head-replay/submission.csv` 와 대조할 때
# (`absence-replay` 와의 대조도 같은 목록이다).
DELIBERATE_MOVES = [
    ("PPS-DEV-01", "v1"), ("PPS-DEV-03", "e3"), ("PPS-DEV-03", "v3"),
    ("PPS-DEV-036", "v19"), ("PPS-DEV-038", "v24"), ("PPS-DEV-039", "v21"),
    ("PPS-DEV-046", "v24"), ("PPS-DEV-047", "v24"), ("PPS-DEV-050", "v9"),
    ("PPS-DEV-060", "v24"),
    ("PPS-DEV-061", "v24"), ("PPS-DEV-062", "v24"), ("PPS-DEV-063", "v12"),
    ("PPS-DEV-066", "e24"), ("PPS-DEV-066", "v24"), ("PPS-DEV-068", "e24"),
    ("PPS-DEV-068", "v24"), ("PPS-DEV-073", "e24"), ("PPS-DEV-073", "v24"),
    ("PPS-DEV-091", "v24"), ("PPS-DEV-092", "v6"), ("PPS-DEV-099", "v24"),
    ("PPS-DEV-101", "v1"), ("PPS-DEV-102", "e6"), ("PPS-DEV-102", "v6"),
    ("PPS-DEV-103", "v24"), ("PPS-DEV-11", "e5"), ("PPS-DEV-11", "v5"),
    ("PPS-DEV-122", "e24"),
    ("PPS-DEV-122", "v24"), ("PPS-DEV-123", "v24"), ("PPS-DEV-127", "v21"),
    ("PPS-DEV-127", "v3"), ("PPS-DEV-130", "v9"), ("PPS-DEV-132", "v9"),
    ("PPS-DEV-144", "v6"),
    ("PPS-DEV-145", "v24"), ("PPS-DEV-148", "e13"), ("PPS-DEV-15", "e24"),
    ("PPS-DEV-15", "v24"), ("PPS-DEV-153", "v24"), ("PPS-DEV-156", "e24"),
    ("PPS-DEV-156", "v24"), ("PPS-DEV-16", "v13"), ("PPS-DEV-162", "v9"),
    ("PPS-DEV-170", "v21"), ("PPS-DEV-176", "v24"),
    ("PPS-DEV-182", "v24"), ("PPS-DEV-187", "v6"),
    ("PPS-DEV-188", "v21"), ("PPS-DEV-191", "e24"), ("PPS-DEV-191", "v24"),
    ("PPS-DEV-192", "e24"), ("PPS-DEV-192", "v24"), ("PPS-DEV-195", "v24"),
    ("PPS-DEV-198", "v13"), ("PPS-DEV-199", "v24"),
    ("PPS-DEV-25", "e3"), ("PPS-DEV-25", "v3"),
    ("PPS-DEV-28", "v24"),
]

# `reports/runs/colab-1789894949866134428/dev-debug/submission.csv` 와 대조할 때.
# 그 회차가 만든 CSV 라 다시 쓰지 않는다. 위 목록과 겹치지만 같지 않다 — 그 회차에만 있는
# `PPS-DEV-036/v5`·`PPS-DEV-042/v21`·`PPS-DEV-169/v24` 가 있고, 위에 있는
# `PPS-DEV-170/v21`·`PPS-DEV-038/v24` 등은 여기 없다.
#  - 여덟 셀: D7 의 적용범위 게이트(v3·v5·v6) 네 자리가 값과 근거를 함께 비웠다.
#    이 회차의 원응답이 그 회차 CSV 와 달라 위 목록과 겹치지 않는 공고가 섞인다.
DELIBERATE_MOVES_H2 = [
    ("PPS-DEV-01", "v1"), ("PPS-DEV-036", "v19"), ("PPS-DEV-036", "v5"),
    ("PPS-DEV-042", "v21"), ("PPS-DEV-046", "v24"), ("PPS-DEV-047", "v24"),
    ("PPS-DEV-050", "v9"),
    ("PPS-DEV-060", "v24"), ("PPS-DEV-061", "v24"), ("PPS-DEV-062", "v24"),
    ("PPS-DEV-063", "v12"), ("PPS-DEV-066", "e24"), ("PPS-DEV-066", "v24"),
    ("PPS-DEV-073", "e24"), ("PPS-DEV-073", "v24"), ("PPS-DEV-09", "e6"),
    ("PPS-DEV-09", "v6"), ("PPS-DEV-091", "v24"), ("PPS-DEV-092", "v6"),
    ("PPS-DEV-099", "v24"), ("PPS-DEV-101", "v1"), ("PPS-DEV-102", "e6"),
    ("PPS-DEV-102", "v6"), ("PPS-DEV-11", "e5"), ("PPS-DEV-11", "v5"),
    ("PPS-DEV-122", "e24"),
    ("PPS-DEV-122", "v24"), ("PPS-DEV-123", "v24"), ("PPS-DEV-127", "v21"),
    ("PPS-DEV-127", "v3"), ("PPS-DEV-130", "v9"),
    ("PPS-DEV-144", "v6"), ("PPS-DEV-148", "e13"),
    ("PPS-DEV-15", "e24"), ("PPS-DEV-15", "v24"), ("PPS-DEV-153", "v24"),
    ("PPS-DEV-156", "e24"), ("PPS-DEV-156", "v24"), ("PPS-DEV-16", "v13"),
    ("PPS-DEV-162", "v9"), ("PPS-DEV-169", "v24"),
    ("PPS-DEV-176", "v24"), ("PPS-DEV-187", "v6"),
    ("PPS-DEV-188", "v21"), ("PPS-DEV-191", "e24"), ("PPS-DEV-191", "v24"),
    ("PPS-DEV-192", "v24"), ("PPS-DEV-195", "v24"), ("PPS-DEV-198", "v13"),
    ("PPS-DEV-25", "e3"),
    ("PPS-DEV-25", "v3"), ("PPS-DEV-28", "v24"),
]

# `reports/team-c/a7-v24-meta-diff/candidate-replay/submission.csv` 와 대조할 때.
# 그 보관본은 이미 A7 대조 축이 적용된 산출물이므로, 지금 `script.py` 와의 차이는
# **근거 계약이 움직인 셀만 남는다** — A7 이 양쪽에 다 있어 상쇄된다. v24·e24 가 한 칸도
# 없는 것이 그 증거다. 이 목록이 달라지면 두 규칙 중 하나의 배선이 끊긴 것이다.
# D7 의 게이트 여덟 셀도 여기에 더해진다 — 그 보관본은 A7 만 적용된 산출물이다.
DELIBERATE_MOVES_A7 = [
    ("PPS-DEV-01", "v1"), ("PPS-DEV-03", "e3"), ("PPS-DEV-03", "v3"),
    ("PPS-DEV-036", "v19"), ("PPS-DEV-039", "v21"), ("PPS-DEV-050", "v9"),
    ("PPS-DEV-063", "v12"),
    ("PPS-DEV-092", "v6"), ("PPS-DEV-101", "v1"), ("PPS-DEV-102", "e6"),
    ("PPS-DEV-102", "v6"), ("PPS-DEV-11", "e5"), ("PPS-DEV-11", "v5"),
    ("PPS-DEV-127", "v21"),
    ("PPS-DEV-127", "v3"), ("PPS-DEV-130", "v9"), ("PPS-DEV-132", "v9"),
    ("PPS-DEV-144", "v6"),
    ("PPS-DEV-148", "e13"), ("PPS-DEV-16", "v13"), ("PPS-DEV-162", "v9"),
    ("PPS-DEV-170", "v21"), ("PPS-DEV-187", "v6"),
    ("PPS-DEV-188", "v21"), ("PPS-DEV-198", "v13"),
    ("PPS-DEV-25", "e3"),
    ("PPS-DEV-25", "v3"),
]


def csv_cell_diff(left: bytes, right: bytes):
    """두 제출 CSV 에서 다른 셀을 `(id, 열)` 로 돌려준다.

    보관 CSV 와의 바이트 동일이 **일부러** 깨졌을 때 쓴다 — 무엇이 몇 셀 움직였는지 세어
    고정하면 바이트 비교의 회귀 검출력을 잃지 않으면서 보관물을 다시 쓰지 않아도 된다.

    그 검출력이 성립하려면 셀을 세기 전에 **구조**를 봐야 한다. 헤더가 다르거나 id 가 중복되면
    셀 비교는 조용히 `[]` 를 돌려준다 — 열이 하나 늘어난 CSV 도, 같은 id 가 두 줄인 CSV 도
    "움직인 셀 없음" 이 된다. 행 순서는 ID 기반 채점이라 보지 않는다.
    """
    import csv as _csv
    import io as _io

    def read(data, side):
        reader = _csv.DictReader(_io.StringIO(data.decode("utf-8-sig")))
        columns = reader.fieldnames
        if not columns:
            raise ValueError(f"{side} CSV 에 헤더가 없다")
        if columns[0] != "id":
            raise ValueError(f"{side} CSV 의 첫 열이 id 가 아니다: {columns[0]!r}")
        if len(set(columns)) != len(columns):
            raise ValueError(f"{side} CSV 의 헤더에 중복 열이 있다")
        rows = {}
        for row in reader:
            # 헤더보다 긴 행은 여분 값을 `None` 키에 넣고, 짧은 행은 결측을 `None` 값으로 넣는다.
            # 선언된 헤더만 순회하면 둘 다 조용히 통과하므로 여기서 거부한다.
            if None in row:
                raise ValueError(f"{side} CSV 의 행이 헤더보다 길다: {row['id']}")
            if any(value is None for value in row.values()):
                raise ValueError(f"{side} CSV 의 행이 헤더보다 짧다: {row['id']}")
            if not row["id"].strip():
                raise ValueError(f"{side} CSV 에 빈 id 행이 있다")
            if row["id"] in rows:
                raise ValueError(f"{side} CSV 에 id 가 중복된다: {row['id']}")
            rows[row["id"]] = row
        if not rows:
            raise ValueError(f"{side} CSV 에 행이 없다")
        return columns, rows

    left_columns, a = read(left, "왼쪽")
    right_columns, b = read(right, "오른쪽")
    if left_columns != right_columns:
        raise ValueError("CSV 의 열 구성이 다르다")
    if set(a) != set(b):
        raise ValueError("CSV 의 id 집합이 다르다")
    return sorted((i, c) for i in b for c in right_columns if a[i][c] != b[i][c])


def to_csv_bytes(script, rows):
    """`script.write_csv`와 같은 바이트를 메모리에서 만든다."""
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=script.HEADER if hasattr(script, "HEADER")
                            else ["id"] + script.ITEMS + [f"e{i}" for i in range(1, 25)],
                            lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode("utf-8")


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure:
            reconfigure(encoding="utf-8")  # 파이프에 붙은 파이썬은 로케일 인코딩으로 죽는다.
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", required=True,
                        help="원응답이 있는 회차 폴더, 예: reports/runs/<run-id>/dev-debug")
    parser.add_argument("--input", default=str(ROOT / "open/dev.jsonl"))
    parser.add_argument("--data-dir", default=str(ROOT / "open/data"))
    parser.add_argument("--script", help="제출 코드. 기본은 저장소 루트의 script.py, --verify면 회차 커밋의 script.py")
    parser.add_argument("--candidate",
                        help="후보 모듈. postprocess·verify_sme·verify_company_size 중 정의한 것만 갈아 끼운다")
    parser.add_argument("--output-dir", help="새 디렉터리. CSV와 기록을 남긴다")
    parser.add_argument("--verify", action="store_true",
                        help="회차 자신의 CSV를 바이트 단위로 재현하는지 확인한다")
    args = parser.parse_args(argv)
    try:
        if args.script:
            script = load_module(Path(args.script), "submission")
        elif args.verify:
            # 재현 확인은 회차의 코드로 한다. HEAD의 후처리 변경과 무관하게 원응답 보관을 검사한다.
            scratch = tempfile.mkdtemp(prefix="replay-script-")
            script = run_script(args.case, scratch)
        else:
            script = load_module(ROOT / "script.py", "submission")
        candidate = load_module(Path(args.candidate), "candidate") if args.candidate else None
        result = replay(script, args.case, input_path=args.input, data_dir=args.data_dir,
                        postprocess=getattr(candidate, "postprocess", None),
                        verify_sme=getattr(candidate, "verify_sme", None),
                        verify_company_size=getattr(candidate, "verify_company_size", None))
        produced = to_csv_bytes(script, result["rows"])
        original = (Path(args.case) / "submission.csv").read_bytes()
        identical = produced == original
        if args.verify:
            if candidate:
                raise ValueError("--verify는 후보 없이, 회차를 그대로 재현할 때만 쓴다")
            if not identical:
                raise ValueError("재생이 회차의 CSV와 다르다. 이 재생 결과를 근거로 쓰지 않는다")
        if args.output_dir:
            out = Path(args.output_dir)
            if out.exists():
                raise ValueError(f"{out} 가 이미 있다. 새 경로를 쓴다")
            out.mkdir(parents=True)
            (out / "submission.csv").write_bytes(produced)
            (out / "manifest.json").write_text(json.dumps({
                "purpose": "cpu_replay_only", "model_called": False,
                "case": script.record_path(str(Path(args.case).resolve())),
                "candidate": script.record_path(args.candidate) if args.candidate else None,
                "matches_original": identical,
                "original_sha256": hashlib.sha256(original).hexdigest(),
                "replayed_sha256": hashlib.sha256(produced).hexdigest(),
                "notices": len(result["rows"]),
                "created_at": datetime.now(timezone.utc).isoformat(),
                "note": "저장된 원응답으로 모델 뒤 단계만 다시 돌렸다. 새 모델 실행이 아니다.",
            }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    except (OSError, ValueError, KeyError, AttributeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"재생 {len(result['rows'])}건 · 회차 CSV와 {'동일' if identical else '다름'}"
          + (f" · 후보 {Path(args.candidate).name}" if args.candidate else ""))
    if args.output_dir:
        print(f"  → {args.output_dir}/submission.csv (tools/score.py로 채점한다)")
    print("모델을 부르지 않았다. 프롬프트·스키마를 바꾸는 후보는 이 경로로 잴 수 없다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
