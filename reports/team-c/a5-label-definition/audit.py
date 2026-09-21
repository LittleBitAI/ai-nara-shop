"""A5 재현용 CPU 진단. 저장소 루트에서 실행하며 새 모델을 호출하지 않는다."""

import csv
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
import script
from experiments.a5_dp_certificate_candidate import pattern
from tools.replay_run import saved_responses

OUT = Path(__file__).resolve().parent
CASE = ROOT / "reports/runs/colab-1789902969401579900/dev-debug"
# 진단용: 명시적으로 '업종코드'라 적힌 네 자리만 비교한다. 업종명·AND/OR는 수동 검토.
INDUSTRY = re.compile(r"업종\s*코드\s*[:：]?\s*(\d{4})(?!\d)")
JOINT = re.compile(r"공동\s*사업")


def spans(rec, expression):
    result = []
    for doc in rec["docs"]:
        offset = 0
        for line_no, line in enumerate(doc["text"].splitlines(keepends=True), 1):
            quote = line.rstrip("\r\n")
            if expression.search(quote):
                result.append(dict(doc_id=doc["doc_id"], line=line_no,
                                   start=offset, end=offset + len(quote), quote=quote))
            offset += len(line)
    return result


def industry(rec):
    registered = set(re.findall(r"(?<!\d)\d{4}(?!\d)", str(rec["meta"].get("면허업종제한목록") or "")))
    observed = set(INDUSTRY.findall("\n".join(d["text"] for d in rec["docs"])))
    return registered, observed


def write(name, data):
    (OUT / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8", newline="\n")


def main():
    assert INDUSTRY.findall("업종코드: 5210 / 제52101조") == ["5210"]
    records = list(script.iter_records(str(ROOT / "open/dev.jsonl")))
    truth = {r["id"]: r for r in csv.DictReader((ROOT / "open/dev_labels.csv").open(encoding="utf-8"))}
    pred = {r["id"]: r for r in csv.DictReader((OUT / "head-replay/submission.csv").open(encoding="utf-8"))}
    responses = saved_responses(CASE)["company_size"]
    script.load_sme_reference(str(ROOT / "open/data"))
    diagnostics = []
    terms = re.compile(r"직접\s*생산|중소기업|소기업|업종|면허|지역제한|본점|소재지|사업금액|용역금액|기초금액|공동사업")
    for rec in records:
        notice_id = rec["id"]
        if not any(truth[notice_id][v] == "1" or pred[notice_id][v] == "1" for v in ("v11", "v13", "v24")):
            continue
        demand, codes = script.direct_production_demand(rec)
        with patch.object(script, "DP_DEMAND", pattern(script)):
            extra_demand, extra_codes = script.direct_production_demand(rec)
        registered, observed = industry(rec)
        found = spans(rec, terms)
        for span in found:
            doc = next(d for d in rec["docs"] if d["doc_id"] == span["doc_id"])
            assert doc["text"][span["start"]:span["end"]] == span["quote"]
        allowed = script.SME_ALLOWED.search(script.build_context(rec, script.PROMPT_BUDGET))
        diagnostics.append(dict(id=notice_id, truth={v:truth[notice_id][v] for v in ("v11","v13","v24")},
            pred={v:pred[notice_id][v] for v in ("v11","v13","v24")}, meta=rec["meta"],
            completeness=rec.get("input_completeness"), demand=demand, codes=sorted(codes),
            competitive=script.competitive_product(rec,codes), certificate_demand=extra_demand,
            certificate_codes=sorted(extra_codes), sme_allowed_match=allowed.group() if allowed else None,
            company_size=json.loads(responses[notice_id])["company_size"],
            industry_registered=sorted(registered), industry_observed=sorted(observed),
            joint_spans=spans(rec,JOINT), spans=found))
    write("cases.json", diagnostics)
    counts = {}
    for name, path in (("dev", ROOT / "open/dev.jsonl"), ("unlabeled", ROOT / "open/train_unlabeled.jsonl")):
        count = dict(n=0, demand_before=0, demand_after=0, demand_added=0,
                     v11_before=0, v11_after=0, v11_added=0, v12_added=0,
                     industry_code_mismatch=0, region_marker=0, region_guard_reached=0)
        mismatch_ids, added_ids, guard_ids = [], [], []
        started = time.perf_counter()
        for rec in script.iter_records(str(path)):
            count["n"] += 1
            before = script.apply_product_rules({}, rec)
            demand_before = script.direct_production_demand(rec)[0]
            with patch.object(script, "DP_DEMAND", pattern(script)):
                after = script.apply_product_rules({}, rec)
                demand_after = script.direct_production_demand(rec)[0]
            count["demand_before"] += demand_before is not None
            count["demand_after"] += demand_after is not None
            count["demand_added"] += demand_before is None and demand_after is not None
            for item in ("v11", "v12"):
                b = before.get(item, {}).get("위반여부") == 1
                a = after.get(item, {}).get("위반여부") == 1
                if item == "v11":
                    count["v11_before"] += b
                    count["v11_after"] += a
                count[item + "_added"] += a and not b
                if a and not b:
                    added_ids.append([rec["id"], item])
            registered, observed = industry(rec)
            mismatch = bool(registered and observed and registered.isdisjoint(observed))
            count["industry_code_mismatch"] += mismatch
            if mismatch:
                mismatch_ids.append(rec["id"])
            marker = "[" in str(rec["meta"].get("제한지역코드목록") or "")
            count["region_marker"] += marker
            if name == "dev" and marker and pred[rec["id"]]["v24"] == "1" and script.V24_REGION.search(pred[rec["id"]]["e24"]):
                count["region_guard_reached"] += 1
                guard_ids.append(rec["id"])
        if name == "unlabeled":
            count["region_guard_reached"] = None  # 모델 응답이 없어 측정할 수 없다.
        counts[name] = dict(counts=count, cpu_seconds=round(time.perf_counter()-started,3),
                            mismatch_ids=mismatch_ids, added_ids=added_ids, guard_ids=guard_ids)
        print(name, count, flush=True)
    rates = {}
    for key in counts["dev"]["counts"]:
        if key in ("n", "region_guard_reached"):
            continue
        d = counts["dev"]["counts"][key] / counts["dev"]["counts"]["n"]
        u = counts["unlabeled"]["counts"][key] / counts["unlabeled"]["counts"]["n"]
        rates[key] = dict(dev_rate=d, unlabeled_rate=u, ratio=u/d if d else None)
    write("audit.json", dict(counts=counts,rates=rates,model_called=False,
        note="무라벨 규칙 단독 발화율. 모델 원응답이 없으므로 최종 예측 발화율은 미측정."))
    paths = [ROOT / "script.py", Path(__file__), ROOT / "experiments/a5_dp_certificate_candidate.py",
             ROOT / "open/dev.jsonl", ROOT / "open/dev_labels.csv", ROOT / "open/train_unlabeled.jsonl",
             CASE / "diagnostics.jsonl", ROOT / "open/data/법령패키지/중기부고시/중기부고시_경쟁제품_세부품명.csv"]
    write("manifest.json",dict(status="draft", reviewer=None, model=None,
        head=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),
        command="python -X utf8 reports/team-c/a5-label-definition/audit.py",
        sha256={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}))


if __name__ == "__main__":
    main()
