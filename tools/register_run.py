"""artifacts/inbox의 결과 ZIP 한 쌍을 reports/runs/<run-id>/에 등록한다. 모델 미사용."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
RESULTS_NAME = re.compile(r"^colab-results-(\d+)\.zip$")
RESULTS_REQUIRED = ("source.json", "runtime.json")
SUBMIT_REQUIRED = ("script.py", "requirements.txt")
MAX_FILE_BYTES = 50 * 1024 * 1024
INDEX_HEADER = "| run-id |"
COMMAND = "python -X utf8 tools/register_run.py --inbox artifacts/inbox --code-commit <커밋>"

# 값이 붙은 것만 위반이다. 환경변수 이름·`hf_xet` 같은 패키지 이름·컨테이너 경로는 오탐이다.
_ASSIGN = r"""(?:\\?["'])?\s*[=:]\s*(?:\\?["'])?"""
_VALUE = r"[A-Za-z0-9._~+/=-]{8,}"
SECRETS = (
    ("HF_TOKEN 값", re.compile(rf"HF_TOKEN{_ASSIGN}{_VALUE}")),
    ("hf_ 토큰", re.compile(r"\bhf_[A-Za-z0-9]{20,}")),
    ("api_key 값", re.compile(rf"api[_-]?key{_ASSIGN}{_VALUE}", re.IGNORECASE)),
    ("Bearer 토큰", re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]{10,}")),
    ("개인 절대 경로", re.compile(r"""[A-Za-z]:[\\/]{1,2}Users[\\/]{1,2}[^\\/\s"']+|/home/[^/\s"']+""")),
)

# 결정 기록 이름에 일련번호를 쓰지 않는다. 공용 위키의 `sync`가 머지된 PR을
# `<날짜>-<PR번호>-<브랜치>`로 캐 넣으므로 번호를 쓰면 PR 번호와 부딪힌다.
# run-id는 그 자체로 유일하므로 번호가 필요 없다.


def safe_parts(name):
    """zip slip 차단. 이름을 믿지 않고 대상 디렉터리 안의 상대 조각만 돌려준다."""
    pure = PurePosixPath(name.replace("\\", "/"))
    if not pure.parts or pure.is_absolute() or ".." in pure.parts or ":" in pure.parts[0]:
        raise ValueError(f"ZIP 경로가 대상 디렉터리 밖으로 나간다: {name!r}")
    return pure.parts


def read_zip(path, required):
    """멤버를 이름→bytes로 읽는다. 경로 이탈·단일 파일 한도·필수 경로를 여기서 막는다."""
    entries = {}
    with zipfile.ZipFile(path) as archive:
        if archive.testzip() is not None:
            raise ValueError(f"{path.name}: ZIP CRC 오류")
        for info in archive.infolist():
            if info.is_dir():
                continue
            safe_parts(info.filename)
            with archive.open(info) as member:
                data = member.read(MAX_FILE_BYTES + 1)  # 헤더의 크기를 믿지 않는다.
            if len(data) > MAX_FILE_BYTES:
                raise ValueError(
                    f"{path.name}: {info.filename} 이 50MB를 넘는다 (선언 {info.file_size}바이트). "
                    "넣지 말고 경로·크기·이유를 남긴다")
            entries[info.filename] = data
    missing = [name for name in required if name not in entries]
    if missing:
        raise ValueError(f"{path.name}: 예상 경로가 없다: {', '.join(missing)}")
    return entries


def scan(entries, archive_name):
    """푼 파일은 텍스트여야 하고, 값이 붙은 비밀·개인 경로가 없어야 한다."""
    for name, data in sorted(entries.items()):
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError(f"{archive_name}: {name} 이 UTF-8 텍스트가 아니다 ({exc.reason})") from exc
        for label, pattern in SECRETS:
            found = pattern.search(text)
            if found:
                line = text.count("\n", 0, found.start()) + 1
                raise ValueError(f"{archive_name}: {name}:{line} 에서 {label} 패턴을 찾았다")


def added(*values):
    """로그에 있는 값만 더한다. 하나라도 없으면 null로 두고 추정하지 않는다."""
    return sum(values) if all(isinstance(value, int) for value in values) else None


def scored_case(entries):
    """어느 case를 채점했는지는 score-command.json의 `--pred` 인자에만 있다. 추측하지 않는다."""
    argv = [str(value) for value in (load_json(entries, "score-command.json").get("argv") or [])]
    for index, argument in enumerate(argv):
        if argument == "--pred" and index + 1 < len(argv):
            return PurePosixPath(argv[index + 1]).parent.name
        if argument.startswith("--pred="):
            return PurePosixPath(argument.split("=", 1)[1]).parent.name
    return None


def load_json(entries, name):
    """로그의 JSON. 없으면 빈 표를 돌려주고 값을 지어내지 않는다."""
    raw = entries.get(name)
    if raw is None:
        return {}
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"{name}: JSON을 읽을 수 없다 ({exc})") from exc
    return data if isinstance(data, dict) else {}


def build_cases(entries):
    """`<case>/run_report.json` 하나가 한 실행 단위다. 없는 값은 null로 남긴다."""
    cases, reports = {}, []
    for name in sorted(entries):
        case, _, tail = name.partition("/")
        if tail != "run_report.json":
            continue
        report = load_json(entries, name)
        command = load_json(entries, f"{case}-command.json")
        reports.append(report)
        cases[case] = {
            "count": report.get("건수"),
            "input_sha256": report.get("input_sha256"),
            "mode": report.get("mode"),
            "seconds": {
                "model_load": report.get("모델로드_s"),
                "baseline_inference": report.get("baseline_inference_seconds"),
                "extra_inference": report.get("sme_inference_seconds"),
                "inference_total": report.get("추론_s"),
                "run_total": report.get("전체_s"),
                "wall_clock": command.get("elapsed_seconds"),
            },
            "counts": {
                "model_success": report.get("model_success_count"),
                "extra_model_success": report.get("sme_model_success_count"),
                # 선택 = 검증 + 폴백. colab.md가 적어 둔 항등식이며 추정치가 아니다.
                "extra_selected": added(report.get("sme_verified_count"),
                                        report.get("sme_fallback_count")),
                "extra_fallback": report.get("sme_fallback_count"),
                "extra_rejected_positive": report.get("sme_rejected_positive_count"),
                "valid_json": report.get("유효JSON"),
                "filled_items": report.get("메운_항목수"),
                "evidence_kept": report.get("근거_유지"),
                "evidence_dropped_not_verbatim": report.get("근거_원문불일치_폐기"),
                "documents_shrunk": report.get("sme_documents_shrunk"),
            },
            "self_check": report.get("자가검증"),
            "macro_f1": None,
        }
    if not cases:
        raise ValueError("결과 ZIP에 <case>/run_report.json 이 없다")
    return cases, reports


def debug_responses(reports):
    """원응답 포함 여부. 로그에 설정이 없으면 추정하지 않고 null로 둔다."""
    flags = []
    for report in reports:
        settings = report.get("reproduction", {})
        settings = settings.get("settings", {}) if isinstance(settings, dict) else {}
        if isinstance(settings, dict) and "debug_responses" in settings:
            flags.append(bool(settings["debug_responses"]))
    return any(flags) if flags else None


def build_manifest(run_id, archive_name, digests, code_commit, entries):
    source = load_json(entries, "source.json")
    recorded = source.get("commit")
    if recorded and not (recorded.startswith(code_commit) or code_commit.startswith(recorded)):
        raise ValueError(f"코드 커밋이 로그와 다르다: --code-commit {code_commit}, "
                         f"source.json {recorded}")
    runtime = load_json(entries, "runtime.json")
    gpus = load_json(entries, "resources.json").get("gpus") or []
    model = load_json(entries, "model.json")
    cases, reports = build_cases(entries)
    final = load_json(entries, "score/metrics.json").get("macro_f1")
    if final is None:
        final = load_json(entries, "validation.json").get("macro_f1")
    scored = scored_case(entries)
    if scored in cases:
        cases[scored]["macro_f1"] = final
    return {
        "run_id": run_id,
        "archive": archive_name,
        "zip_sha256": digests,
        "registered_at": datetime.now(timezone.utc).isoformat(),
        "code": {
            "repository": source.get("url"),
            "requested_ref": source.get("requested_ref"),
            "commit": recorded or code_commit,
            "given_commit": code_commit,
        },
        "environment": {
            "gpu": runtime.get("gpu"),
            "gpu_detail": gpus[0] if gpus else None,
            "python": runtime.get("python"),
            "cuda": runtime.get("cuda"),
            "packages": runtime.get("packages"),
            "model": {"id": model.get("id"), "revision": model.get("revision")},
            "notebook_python": load_json(entries, "host.json").get("python"),
        },
        "cases": cases,
        "score": {
            "final_macro_f1": final,
            "baseline_macro_f1_same_run": load_json(entries, "score-baseline/metrics.json").get("macro_f1"),
            "source": "score/metrics.json, score-baseline/metrics.json, validation.json",
            "note": "이 실행이 기록한 값을 그대로 옮겼다. 재계산하지 않았다.",
        },
        "raw_responses": {"included": debug_responses(reports),
                          "source": "reproduction.settings.debug_responses"},
    }


def environment_summary(environment):
    packages = environment.get("packages") or {}
    parts = [environment.get("gpu")]
    if packages.get("vllm"):
        parts.append(f"vLLM {packages['vllm']}")
    if environment.get("cuda"):
        parts.append(f"CUDA {environment['cuda']}")
    return ", ".join(part for part in parts if part) or "미보관"


def index_row(manifest):
    run_id = manifest["run_id"]
    commit = (manifest["code"]["commit"] or "")[:7] or "미상"
    score = manifest["score"]["final_macro_f1"]
    raw = {True: "포함", False: "없음", None: "미상"}[manifest["raw_responses"]["included"]]
    folder = f"reports/runs/{run_id}/"
    return (f"| `{run_id}` | `{commit}` | {'' if score is None else repr(score)} | "
            f"{environment_summary(manifest['environment'])} | {raw} | [{folder}](../{folder}) |\n")


def upsert_row(text, run_id, row):
    """한 행이 한 실행이다. 이미 `미보관`으로 있던 실행이면 그 행을 채우고, 없으면 덧붙인다."""
    lines = text.splitlines(keepends=True)
    start = next((i for i, line in enumerate(lines) if line.startswith(INDEX_HEADER)), None)
    if start is None:
        raise ValueError(f"docs/runs.md 에서 색인 표 머리글 {INDEX_HEADER!r} 을 찾지 못했다")
    end = start
    while end < len(lines) and lines[end].startswith("|"):
        end += 1
    existing = next((i for i in range(start, end) if lines[i].startswith(f"| `{run_id}` |")), None)
    if existing is None:
        return "".join(lines[:end] + [row] + lines[end:])
    return "".join(lines[:existing] + [row] + lines[existing + 1:])


def decision_draft(manifest, files, largest):
    """훅이 제목과 '왜.' 첫 문장을 요약으로 싣는다. 로그 본문은 넣지 않는다."""
    run_id = manifest["run_id"]
    score = manifest["score"]["final_macro_f1"]
    cases = ", ".join(f"{name} {case['count']}건" for name, case in manifest["cases"].items())
    title = f"run: {run_id} 결과 ZIP을 실행 기록에 등록"
    digests = manifest["zip_sha256"]
    return (
        "---\n"
        "scope: project\n"
        "severity: preference\n"
        f'triggers: ["실행 기록", "run", "runs", "colab", "{run_id}", "manifest", "등록"]\n'
        "domain: 'run-archive'\n"
        f'title: "{title}"\n'
        "---\n"
        f"\n# {title}\n\n"
        f"무엇. `artifacts/inbox`의 `{manifest['archive']}`를 `tools/register_run.py`로 등록했습니다.\n"
        f"결과 ZIP의 파일 {files}개를 `reports/runs/{run_id}/`에 텍스트로 풀었고 ZIP 바이너리는\n"
        "커밋하지 않았습니다. 두 ZIP 해시·코드 커밋·실행 환경·시간·건수·원응답 여부는 같은 폴더의\n"
        f"`manifest.json`에 있습니다. 제출 ZIP 해시의 출처는 `{manifest['zip_sha256_source']['submit']}`입니다.\n\n"
        f"왜. 이 등록은 `{(manifest['code']['commit'] or '')[:7]}` 코드가 "
        f"{environment_summary(manifest['environment'])}에서 {cases}을 완주하고 "
        f"{'점수 기록 없이 끝났다' if score is None else f'Macro F1 {score!r}을 남겼다'}는 것만 "
        "기록하고 대회 서버 제출 성공을 증명하지 않습니다.\n"
        "수치는 실행이 남긴 파일에서 그대로 옮겼고 등록 과정에서 다시 계산하지 않았습니다.\n"
        f"등록 검사: 결과 ZIP SHA-256 `{digests['results'][:8]}…{digests['results'][-5:]}`, "
        f"제출 ZIP SHA-256 `{digests['submit'][:8]}…{digests['submit'][-5:]}`, "
        f"파일 {files}개 UTF-8 해독, 최대 파일 {largest // 1024}KB로 50MB 한도 아래,\n"
        "비밀정보 패턴 0건, ZIP 경로 이탈 0건. 이 문서는 초안이며 사람이 확인한 뒤 커밋합니다.\n\n"
        f"출처. `docs/runs.md` · `reports/runs/{run_id}/manifest.json` · `tools/register_run.py`\n"
    )


def write_run_directory(target, entries, manifest):
    """검사를 다 통과한 뒤에만 쓴다. 완성한 폴더를 rename으로 한 번에 올린다."""
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".register-", dir=target.parent) as temporary:
        staged = Path(temporary) / target.name
        staged.mkdir()
        for name, data in entries.items():
            path = staged.joinpath(*safe_parts(name))
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)  # 로그 바이트는 고치지 않는다.
        (staged / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
            encoding="utf-8", newline="\n")
        staged.rename(target)


def register(inbox, code_commit, *, root=ROOT, expect_results=None, expect_submit=None):
    candidates = sorted(p for p in inbox.glob("colab-results-*.zip") if RESULTS_NAME.match(p.name))
    if len(candidates) != 1:
        raise ValueError(f"{inbox}: colab-results-<숫자>.zip 후보가 {len(candidates)}개다. "
                         "한 개만 두고 다시 실행한다")
    results_zip = candidates[0]
    run_id = "colab-" + RESULTS_NAME.match(results_zip.name).group(1)
    target = root / "reports/runs" / run_id
    if target.exists():
        raise ValueError(f"reports/runs/{run_id} 가 이미 있다. 덮어쓰지 않는다")

    entries = read_zip(results_zip, RESULTS_REQUIRED)
    # 품질 게이트 미달이면 노트북이 submit.zip을 안 내려준다. 그때는 실행이 적어 둔 해시를 쓴다.
    submit_zip = inbox / "submit.zip"
    recorded = (load_json(entries, "candidate.json").get("submit_sha256")
                or load_json(entries, "validation.json").get("submit_sha256"))
    if submit_zip.is_file():
        submit_digest = hashlib.sha256(submit_zip.read_bytes()).hexdigest()
        submit_source = "artifacts/inbox/submit.zip"
        if recorded and recorded.lower() != submit_digest:
            raise ValueError(f"submit.zip 이 이 실행이 검증한 ZIP이 아니다: "
                             f"실행 기록 {recorded.lower()}, 실제 {submit_digest}")
        read_zip(submit_zip, SUBMIT_REQUIRED)
    elif recorded:
        submit_digest, submit_source = recorded.lower(), "candidate.json"
    else:
        raise ValueError(f"{inbox}: submit.zip 이 없고 결과 ZIP에도 submit_sha256 기록이 없다")

    digests = {"results": hashlib.sha256(results_zip.read_bytes()).hexdigest(),
               "submit": submit_digest}
    for role, expected in (("results", expect_results), ("submit", expect_submit)):
        if expected and expected.lower() != digests[role]:
            raise ValueError(f"{role} ZIP의 SHA-256이 기대값과 다르다: "
                             f"기대 {expected.lower()}, 실제 {digests[role]}")

    if "manifest.json" in entries:
        raise ValueError(f"{results_zip.name}: manifest.json 이 이미 있다. 등록 기록을 덮어쓰지 않는다")
    scan(entries, results_zip.name)

    manifest = build_manifest(run_id, results_zip.name, digests, code_commit, entries)
    manifest["zip_sha256_source"] = {"results": "artifacts/inbox/" + results_zip.name,
                                     "submit": submit_source}
    index_path = root / "docs/runs.md"
    index = upsert_row(index_path.read_text(encoding="utf-8"), run_id, index_row(manifest))
    decisions = root / ".wiki/decisions"
    if not decisions.is_dir():
        raise ValueError(f"{decisions} 가 없다. 결정 초안을 쓸 자리를 먼저 확인한다")
    decision = decisions / f"{datetime.now().strftime('%Y-%m-%d')}-run-{run_id}.md"
    if decision.exists():
        raise ValueError(f"{decision} 가 이미 있다. 덮어쓰지 않는다")
    draft = decision_draft(manifest, len(entries), max(len(data) for data in entries.values()))

    write_run_directory(target, entries, manifest)
    index_path.write_text(index, encoding="utf-8", newline="\n")
    decision.write_text(draft, encoding="utf-8", newline="\n")
    return {"run_id": run_id, "run_dir": target, "decision": decision,
            "files": len(entries), "macro_f1": manifest["score"]["final_macro_f1"]}


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure:
            reconfigure(encoding="utf-8")  # 파이프에 붙은 파이썬은 로케일 인코딩으로 죽는다.
    parser = argparse.ArgumentParser(description=__doc__, epilog=f"등록 절차의 명령: {COMMAND}")
    parser.add_argument("--inbox", type=Path, default=ROOT / "artifacts/inbox")
    parser.add_argument("--code-commit", required=True, help="실행한 코드 커밋. source.json과 대조한다")
    parser.add_argument("--expect-results", help="결과 ZIP의 기대 SHA-256")
    parser.add_argument("--expect-submit", help="제출 ZIP의 기대 SHA-256")
    parser.add_argument("--root", type=Path, default=ROOT, help="등록 대상 저장소 루트")
    args = parser.parse_args(argv)
    try:
        summary = register(args.inbox, args.code_commit, root=args.root,
                           expect_results=args.expect_results, expect_submit=args.expect_submit)
    except (OSError, ValueError, zipfile.BadZipFile) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"등록 {summary['run_id']}: 파일 {summary['files']}개 → reports/runs/{summary['run_id']}/, "
          f"Macro F1 {summary['macro_f1']}, 색인 1행, 결정 초안 {summary['decision'].name}")
    print("초안·색인은 사람이 확인한 뒤 커밋한다. 서버 제출 성공은 이 등록으로 증명되지 않는다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
