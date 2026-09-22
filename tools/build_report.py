"""회차 결과를 web/ 화면이 읽을 JSON으로 만든다. 채점은 tools/score.py 한 곳에서만 한다.

입력은 셋 중 하나다.
  --zip artifacts/inbox/colab-results-<run-id>.zip   새로 받은 결과 ZIP
  --run colab-<run-id>                               이미 등록된 reports/runs/<run-id>/
  --all                                              등록된 회차 전부 (추이선 채우기)

공고 원문·정답 e열은 여기에 담지 않는다. 화면이 open/dev.jsonl·open/dev_labels.csv를
Vite로 직접 읽으므로 사본을 만들 이유가 없다. --share만 원문 없는 요약 HTML을 따로 뽑는다.
"""

import argparse
import csv
from datetime import datetime, timezone
import html
import importlib.util
import io
import json
from pathlib import Path, PurePosixPath
import re
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
TRUTH = ROOT / "open/dev_labels.csv"
OUT_DIR = ROOT / "web/public/runs"
ABSENCE = {10, 11, 16, 18, 20}
RUN_ID = re.compile(r"^[A-Za-z0-9._-]+$")
# register_run.py 와 같은 이름 규약이다. run-id 를 파일명에서 캐므로 아무 이름이나 받으면
# 쓰레기 run-id 가 만들어진다. 이름이 바뀌는 건 뒤의 숫자뿐이고 그 숫자가 run-id 다.
RESULTS_NAME = re.compile(r"^colab-results-(\d+)\.zip$")
INBOX = ROOT / "artifacts/inbox"
# 파일럿 회차는 제출 회차가 아니다. `company_size` 같은 한 단계만 GPU 로 돌리고 나머지는
# 보관 원응답으로 재생하므로, 회차 하나가 (군 × 소비자) 만큼의 CSV 를 낸다. 그 CSV 는
# 제출물과 같은 49열이라 화면의 "한 항목 = CSV 하나" 전제는 그대로 두고, 대신
# `<run-id>.<군>-<소비자>` 라는 별도 항목으로 편다.
PILOT_CSV = "pilot/*/*/*-hybrid.csv"
PILOT_SEP = "."
KIND_RUN, KIND_PILOT = "gpu-run", "gpu-pilot"
# grid 한 칸의 뜻. 화면(web/src/data.js)의 KIND와 같은 글자를 쓴다.
TP, FP, FN, TN = "T", "P", "N", "."


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_score():
    return load_module("score_tool", ROOT / "tools/score.py")


def safe_member(name):
    """zip slip 차단. register_run.py와 같은 이유로 ZIP 안의 이름을 믿지 않는다.

    PurePosixPath로 본다. Windows의 Path는 드라이브 없는 `/abs.csv`를 절대 경로로 안 본다.
    """
    pure = PurePosixPath(name.replace("\\", "/"))
    if not pure.parts or pure.is_absolute() or ".." in pure.parts or ":" in pure.parts[0]:
        raise ValueError(f"ZIP 경로가 대상 밖으로 나간다: {name!r}")
    return "/".join(pure.parts)


def rel(path):
    """메시지에 남길 경로. score.portable 과 같은 이유로 저장소 밖 절대 경로를 안 드러낸다."""
    try:
        return Path(path).resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return Path(path).name


def newest_zip(inbox):
    """받은 함에서 가장 최근 결과 ZIP. 회차마다 이름이 바뀌므로 런처가 이름을 못 박지 않는다."""
    found = [p for p in inbox.glob("colab-results-*.zip") if RESULTS_NAME.match(p.name)]
    if not found:
        raise ValueError(f"{rel(inbox)} 에 colab-results-<숫자>.zip 이 없다")
    return max(found, key=lambda p: p.stat().st_mtime)


def pilot_variants(base):
    """이 회차가 파일럿이면 `(변이 이름, 그 CSV 경로)` 목록. 아니면 빈 목록.

    이름은 `<군>-<소비자>` 다. `pilot/episode-1/control/head-hybrid.csv` → `control-head`.
    """
    found = []
    for path in sorted(base.glob(PILOT_CSV)):
        found.append((f"{path.parent.name}-{path.stem.removesuffix('-hybrid')}", path))
    return found


def split_variant(run):
    """`<run-id>.<변이>` 를 갈라 준다. 변이가 없으면 (run, None)."""
    head, sep, tail = run.rpartition(PILOT_SEP)
    return (head, tail) if sep and (ROOT / "reports/runs" / head).is_dir() else (run, None)


def read_source(args):
    """(run_id, {경로: bytes}, 원본경로, kind) 를 돌려준다. ZIP도 디렉터리도 같은 모양이다.

    파일럿 변이는 그 군·소비자의 `*-hybrid.csv` 를 `dev/submission.csv` 자리에 끼운다.
    그 CSV 가 제출물과 같은 49열이라 `build()` 의 채점·격자 코드는 한 글자도 안 바뀐다.
    **무엇을 읽었는지 아는 것은 여기뿐이므로 `kind` 도 여기서 정해 넘긴다.**
    """
    if args.zip:
        name = RESULTS_NAME.match(args.zip.name)
        if not name:
            raise ValueError(
                f"{args.zip.name}: 이름이 colab-results-<숫자>.zip 이 아니다. "
                "run-id 를 이 숫자에서 캐므로 이름을 바꾸면 회차가 어긋난다")
        run_id = f"colab-{name.group(1)}"
        with zipfile.ZipFile(args.zip) as archive:
            if archive.testzip() is not None:
                raise ValueError(f"{args.zip.name}: ZIP CRC 오류")
            entries = {
                safe_member(i.filename): archive.read(i)
                for i in archive.infolist() if not i.is_dir()
            }
        return run_id, entries, args.zip, KIND_RUN
    run, variant = split_variant(args.run)
    base = ROOT / "reports/runs" / run
    if variant is not None:
        picked = dict(pilot_variants(base)).get(variant)
        if picked is None:
            known = ", ".join(name for name, _ in pilot_variants(base)) or "없음"
            raise ValueError(f"{args.run}: 파일럿 변이 {variant!r} 가 없다. 있는 것: {known}")
        return args.run, {"dev/submission.csv": picked.read_bytes()}, picked, KIND_PILOT
    if not (base / "dev/submission.csv").is_file():
        hint = pilot_variants(base)
        if hint:
            names = ", ".join(f"{run}{PILOT_SEP}{name}" for name, _ in hint)
            raise ValueError(f"{run}: dev/submission.csv 가 없다. 파일럿 회차이므로 "
                             f"변이를 고른다 — {names}")
        raise ValueError(f"{run}: dev/submission.csv 가 없다")
    entries = {
        p.relative_to(base).as_posix(): p.read_bytes()
        for p in base.rglob("*") if p.is_file()
    }
    return run, entries, base, KIND_RUN


def parse_diagnostics(blob):
    """진단 로그를 id별로 접는다. 깨진 줄은 회차 전체를 버리지 않고 건너뛴다."""
    per_id, settings = {}, None
    for line in blob.decode("utf-8").splitlines():
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        name, identifier = event.get("event"), event.get("id")
        if name == "run_started":
            settings = event.get("settings")
        if not identifier:
            continue
        slot = per_id.setdefault(identifier, {})
        if name == "company_size_verified":
            slot["company_size"] = {k: event[k] for k in ("reason", "flags") if k in event}
        elif name == "sme_verified":
            slot["sme"] = {k: event[k] for k in ("rejected_conditions", "flags") if k in event}
        elif name == "response":
            slot.setdefault("responses", []).append({
                k: event.get(k) for k in
                ("phase", "status", "attempt", "response_chars", "output_tokens", "finish_reason")
            })
            if event.get("response_text"):
                slot.setdefault("raw", []).append(
                    {"phase": event.get("phase"), "text": event["response_text"]})
    return per_id, settings


def read_pred(score, blob):
    """검증과 v값은 score.load_csv가 소유한다. 여기서는 e열만 더 꺼낸다."""
    with tempfile.TemporaryDirectory(prefix=".build-report-") as temporary:
        staged = Path(temporary) / "submission.csv"
        staged.write_bytes(blob)
        pred, pred_hash = score.load_csv(staged)
    reader = csv.reader(io.StringIO(blob.decode("utf-8"), newline=""))
    next(reader)
    quotes = {row[0]: row[25:] for row in reader}
    return pred, quotes, pred_hash


def build(score, run_id, entries, source_path, kind=KIND_RUN):
    """`kind` 는 **호출자가 준다.** 여기서 run_id 로 파일시스템을 다시 조회하지 않는다 —
    무엇을 읽었는지는 `read_source` 가 이미 알고, 다시 캐면 저장소 밖에서 만든 입력이
    조용히 제출 회차로 찍힌다. 실제로 검사가 그 모양으로 걸렸다."""
    if "dev/submission.csv" not in entries:
        raise ValueError(f"{run_id}: dev/submission.csv 가 없다")
    truth, _ = score.load_csv(TRUTH)
    pred, quotes, pred_hash = read_pred(score, entries["dev/submission.csv"])
    metrics, _ = score.calculate(truth, pred)

    trace, settings = {}, None
    if "dev/diagnostics.jsonl" in entries:
        trace, settings = parse_diagnostics(entries["dev/diagnostics.jsonl"])

    # 원응답은 dev-debug 에만 남는데 그건 **별도 추론**이다. colab-1789902969401579900 은
    # 두 CSV 가 18셀 다르고 PPS-DEV-03/v3 은 dev 0 · dev-debug 1 이다. 통째로 합치면 채점된
    # 칸을 열었을 때 다른 추론의 판정을 보게 되고, 통째로 막으면 멀쩡한 199건까지 잃는다.
    # 그래서 **24칸이 같은 공고에만** 붙이고, 거기서도 원응답만 가져온다 — 토큰 수·응답 길이는
    # 그 추론의 것이라 dev 것을 덮으면 안 된다.
    raw_note = None
    debug_csv = entries.get("dev-debug/submission.csv")
    if debug_csv is not None:
        debug_pred, debug_quotes, _ = read_pred(score, debug_csv)
        # v값 24칸만 보면 모자란다. 같은 회차의 v값이 같은 183건 중 3칸의 e열이 다르고,
        # PPS-DEV-050/e24 는 **dev 가 빈칸인데 dev-debug 에는 개찰 문구가 들어 있다** —
        # "근거 없음" 진단 아래에 그와 모순되는 원응답이 붙는다. 49열 전체가 같아야 붙인다.
        same = {
            i for i in pred
            if pred[i] == debug_pred.get(i) and quotes[i] == debug_quotes.get(i)
        }
        # 49열이 같아도 **같은 응답은 아니다.** 일치하는 180건의 response 이벤트 451개 중
        # 31개는 길이가 다르다 — PPS-DEV-08/baseline 이 dev 1033자 · dev-debug 1079자다.
        # 그래서 dev 슬롯에 섞지 않고 `debug` 묶음으로 따로 싣는다. 원응답과 그 통계가
        # 한 묶음에 있어야 화면이 "이건 다른 추론의 것" 이라고 말할 수 있다.
        per_id, _ = parse_diagnostics(entries.get("dev-debug/diagnostics.jsonl", b""))
        for identifier in same:
            slot = per_id.get(identifier)
            if slot and "raw" in slot:
                trace.setdefault(identifier, {})["debug"] = {
                    "raw": slot["raw"],
                    "responses": slot.get("responses", []),
                }
        skipped = len(pred) - len(same)
        if skipped:
            raw_note = (f"dev-debug 의 49열이 dev 와 다른 공고 {skipped}건에는 원응답을 안 붙였다. "
                        "같은 ZIP 이어도 별도 추론이라 그 칸들의 판정·근거가 어긋난다")

    has_raw = any("debug" in slot for slot in trace.values())

    grid, evidence = {}, {}
    for identifier in sorted(truth):
        cells = []
        for index, (actual, predicted) in enumerate(zip(truth[identifier], pred[identifier]), 1):
            cells.append(TP if actual and predicted else
                         TN if not actual and not predicted else
                         FP if predicted else FN)
            if predicted and index not in ABSENCE and quotes[identifier][index - 1]:
                evidence.setdefault(identifier, {})[f"v{index}"] = quotes[identifier][index - 1]
        grid[identifier] = "".join(cells)

    return {
        "run_id": run_id,
        # 저울이 다른 것을 한 추이선에 그리지 않으려고 화면이 읽는다. 파일럿은 한 단계만
        # GPU 로 돌리고 나머지는 보관 원응답으로 재생한 값이라 전체 GPU 점수가 아니다.
        "kind": kind,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source": {"path": score.portable(source_path), "pred_sha256": pred_hash},
        "settings": settings,
        "macro_f1": metrics["macro_f1"],
        "items": metrics["items"],
        "ids": sorted(truth),
        "grid": grid,
        "evidence": evidence,
        "trace": trace,
        "has_raw": has_raw,
        "raw_note": raw_note,
    }


def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, allow_nan=False) + "\n",
                    encoding="utf-8", newline="\n")


def refresh_index():
    """회차 추이선과 회차 고르개가 읽는 목록. 빌드된 회차만 담는다."""
    runs = []
    for path in sorted(OUT_DIR.glob("*.json")):
        if path.name == "index.json":
            continue
        report = json.loads(path.read_text(encoding="utf-8"))
        runs.append({
            "run_id": report["run_id"],
            "kind": report.get("kind", KIND_RUN),   # 옛 빌드본에는 없다. 제출 회차로 읽는다
            "created_at": report["created_at"],
            "macro_f1": report["macro_f1"],
            "has_raw": report["has_raw"],
            "items_f1": {name: item["f1"] for name, item in report["items"].items()},
        })
    runs.sort(key=lambda r: r["run_id"])
    write_json(OUT_DIR / "index.json", {"runs": runs})
    return runs


BAR = ('<div class=row><span class=name>{item} {label}</span>'
       '<span class=track><i style="width:{pct:.1f}%"></i></span>'
       '<span class=num>{f1:.3f}</span>'
       '<span class=num dim>TP {tp} · FP {fp} · FN {fn}</span></div>')


def share_html(report, names, history):
    """원문·e열·원응답을 뺀 요약 한 장. Slack에 그냥 던져도 열린다."""
    order = sorted(report["items"].items(), key=lambda kv: (kv[1]["f1"], kv[0]))
    bars = "\n".join(
        BAR.format(item=name, label=html.escape(names.get(name, "")), f1=m["f1"],
                   pct=m["f1"] * 100, tp=m["tp"], fp=m["fp"], fn=m["fn"])
        for name, m in order)
    trend = " · ".join(f'{r["run_id"].rsplit("-", 1)[-1][-4:]} {r["macro_f1"]:.4f}'
                       for r in history[-8:])
    errors = "".join(
        f"<li><code>{html.escape(i)}</code> {name} "
        f'{"놓침" if c == FN else "헛짚음"}</li>'
        for i in report["ids"]
        for name, c in zip(report["items"], report["grid"][i])
        if c in (FP, FN))
    return f"""<!doctype html><html lang=ko><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>{html.escape(report["run_id"])} 채점 요약</title>
<style>
:root{{color-scheme:light dark;--bg:#fcfcfb;--fg:#0b0b0b;--dim:#52514e;--line:#e6e5e0;--bar:#2a78d6}}
@media (prefers-color-scheme:dark){{:root{{--bg:#1a1a19;--fg:#fff;--dim:#c3c2b7;--line:#33332f;--bar:#3987e5}}}}
body{{background:var(--bg);color:var(--fg);font:15px/1.6 system-ui,'Malgun Gothic',sans-serif;
margin:0;padding:32px 24px;max-width:860px}}
h1{{font-size:20px;margin:0 0 4px}}
.lede{{color:var(--dim);margin:0 0 28px;font-size:13px}}
.row{{display:grid;grid-template-columns:1fr 120px 56px 150px;gap:12px;align-items:center;
padding:5px 0;border-bottom:1px solid var(--line)}}
.name{{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
.track{{background:var(--line);height:8px;border-radius:4px;overflow:hidden}}
.track i{{display:block;height:100%;background:var(--bar);border-radius:4px}}
.num{{font:13px/1 ui-monospace,Consolas,monospace;text-align:right;font-variant-numeric:tabular-nums}}
.num.dim{{color:var(--dim);text-align:left}}
h2{{font-size:14px;margin:32px 0 8px}}
ul{{columns:3;font:12px/1.8 ui-monospace,Consolas,monospace;padding-left:18px;color:var(--dim)}}
@media (max-width:640px){{.row{{grid-template-columns:1fr 70px 48px}}.row .dim{{display:none}}ul{{columns:1}}}}
</style>
<h1>{html.escape(report["run_id"])} · Macro F1 {report["macro_f1"]:.6f}</h1>
<p class=lede>공고 원문·근거 문구·모델 원응답은 이 요약에 없다. 전체는 저장소에서 <code>npm run dev</code>.<br>
회차 추이 {html.escape(trend)}</p>
{bars}
<h2>오답 {errors.count("<li>")}건</h2>
<ul>{errors}</ul>
"""


def item_index():
    """docs/items.md 의 전체 항목 표를 읽는다. 번호의 뜻을 화면이 추측하지 않게 한다."""
    text = (ROOT / "docs/items.md").read_text(encoding="utf-8")
    rows = re.findall(r"^\| \[(v\d+)\]\(#v\d+\) \| (.+?) \| (예|아니요) \|", text, re.M)
    if len(rows) != 24:
        raise ValueError(f"docs/items.md 항목표에서 24행을 못 읽었다: {len(rows)}행")
    index = {name: {"name": label, "absence": flag == "예"} for name, label, flag in rows}
    declared = {f"v{i}" for i in ABSENCE}
    found = {name for name, item in index.items() if item["absence"]}
    if declared != found:
        raise ValueError(f"부재탐지 항목이 items.md와 어긋난다: {sorted(declared ^ found)}")
    return index


def item_names():
    return {name: item["name"] for name, item in item_index().items()}


def law_map():
    """항목표의 근거 조문 인용을 제공 법령 원문의 **자리**로 푼다. 조회는 experiments/law_index.py 다.

    화면이 묻는 것은 "v1 의 근거가 어느 법령의 어디인가" 인데, 항목표는 문자열
    `국가계약법 시행령 제12조 국가계약법 시행령 제21조` 만 준다. 한 항목이 법령 여러 개에
    걸치고, 같은 조문을 항목 여럿이 나눠 쓴다. 그 대조를 눈으로 하지 않게 여기서 편다.

    조각마다 원문에서의 시작 오프셋을 같이 싣는다. 미니맵이 그걸로 420,768자 문서 안의
    어디를 인용했는지 그린다. 조각 본문은 `law_index` 가 돌려준 원문 부분문자열 그대로다 —
    다듬으면 인용 검증과 어긋난다.
    """
    law_index = load_module("law_index", ROOT / "experiments/law_index.py")
    data_dir = str(ROOT / "open/data")
    texts = law_index.laws(data_dir)
    table = json.loads((ROOT / "open/data/항목표.json").read_text(encoding="utf-8"))["항목"]

    segments = []
    seen = {}
    cites = {}
    for name, row in table.items():
        axes = {}
        for axis, column in (("국가", "국가계약법"), ("지방", "지방계약법")):
            citation = (row.get(column) or "").strip()
            entry = {"citation": citation, "segs": []}
            found = []
            if citation:
                try:
                    found = law_index.resolve(citation, data_dir)
                except ValueError as exc:
                    # 조용히 빼면 근거 없는 칸이 "근거 있음" 으로 보인다. 화면에 그대로 띄운다.
                    entry["error"] = str(exc)
            for segment in found:
                key = (segment.law, segment.address)
                if key not in seen:
                    seen[key] = len(segments)
                    segments.append({
                        "law": segment.law,
                        "path": list(segment.path),
                        "at": texts[segment.law].find(segment.text),
                        "chars": len(segment.text),
                        "text": segment.text,
                    })
                entry["segs"].append(seen[key])
            axes[axis] = entry
        cites[name] = axes
    return {"laws": {law: {"chars": len(text)} for law, text in texts.items()},
            "segments": segments, "cites": cites}


def amount_bands():
    """금액 구간 필터가 쓰는 경계. script.py의 상수가 원본이고 여기서 베끼지 않는다.

    실행하지 않고 글자로만 읽는다 — 제출 스크립트를 화면 도구가 import할 이유가 없다.
    """
    text = (ROOT / "script.py").read_text(encoding="utf-8")
    bands = {}
    for key, name in (("notice", "NOTICE_AMOUNT_WON"), ("sme_floor", "SME_BAND_FLOOR_WON")):
        found = re.search(rf"^{name} = ([\d_]+)$", text, re.M)
        if not found:
            raise ValueError(f"script.py에서 {name} 을 못 읽었다")
        bands[key] = int(found.group(1).replace("_", ""))
    return bands


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--zip", type=Path, help="결과 ZIP 경로를 직접 준다")
    group.add_argument("--latest", action="store_true",
                       help="받은 함에서 가장 최근 결과 ZIP을 고른다. 런처가 쓰는 길이다")
    group.add_argument("--run", help="등록된 run-id")
    group.add_argument("--all", action="store_true", help="등록된 회차 전부 다시 만든다")
    parser.add_argument("--inbox", type=Path, default=INBOX, help="--latest 가 뒤질 폴더")
    parser.add_argument("--share", action="store_true",
                        help="원문 없는 요약 HTML을 reports/runs/<run-id>/share.html 로 같이 뽑는다")
    args = parser.parse_args()

    if args.latest:
        args.zip = newest_zip(args.inbox)
        print(f"받은 함에서 고름: {rel(args.zip)}")

    score = load_score()
    targets = []
    if args.all:
        targets = [p.parent.parent.name for p in
                   sorted((ROOT / "reports/runs").glob("*/dev/submission.csv"))]
        # 파일럿 회차는 `dev/submission.csv` 가 없어 위 탐색에 안 걸린다. 군·소비자마다
        # 한 항목으로 편다. 이 줄이 없으면 회차를 등록해도 화면에 영영 안 실린다.
        for base in sorted((ROOT / "reports/runs").glob("*")):
            targets += [f"{base.name}{PILOT_SEP}{name}" for name, _ in pilot_variants(base)]
    elif args.run:
        if not RUN_ID.match(args.run):
            raise ValueError(f"run-id 형식이 아니다: {args.run!r}")
        targets = [args.run]

    built = []
    for run in targets or [None]:
        if run is not None:
            args.run = run
            args.zip = None
        run_id, entries, source_path, kind = read_source(args)
        report = build(score, run_id, entries, source_path, kind)
        write_json(OUT_DIR / f"{run_id}.json", report)
        built.append(report)
        print(f"{run_id}: Macro F1={report['macro_f1']:.12g} "
              f"원응답={'있음' if report['has_raw'] else '없음'}")

    write_json(OUT_DIR.parent / "items.json",
               {"items": item_index(), "bands": amount_bands()})
    write_json(OUT_DIR.parent / "laws.json", law_map())
    history = refresh_index()
    if args.share:
        names = item_names()
        for report in built:
            target = ROOT / "reports/runs" / report["run_id"] / "share.html"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(share_html(report, names, history), encoding="utf-8", newline="\n")
            print(f"  요약: {score.portable(target)}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, zipfile.BadZipFile) as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
