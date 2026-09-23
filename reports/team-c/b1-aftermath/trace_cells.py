"""B1 회차가 남긴 미확인 4건 — 바뀐 셀의 경로를 사실 단위로 분해한다.

모델을 부르지 않는다. 기준 회차(colab-1789902969401579900)와 후보 회차
(colab-1790141677344456786)의 **보관 원응답**을 각각 파이프라인에 태워
어느 사실이 달라졌고 어느 게이트에서 갈렸는지 건별로 낸다.

    py -X utf8 reports/team-c/b1-aftermath/trace_cells.py <기준 재생 CSV>

기준은 **판정 당시 코드(57e6134 의 script.py)로 재생한 CSV** 다. 보관 회차의
submission.csv 를 기준으로 쓰면 그 뒤에 병합된 후처리가 섞인다(docs/workflow.md W5).
그 사이 D 파트의 v3~v6 게이트가 머지돼 현재 HEAD 재생은 0.618427228373 이고
판정 당시 기준은 0.609274806721 이다 — 판정을 만든 코드로 재현해야 같은 34셀이 나온다.
"""
import csv
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "reports/runs/colab-1789902969401579900/dev-debug"   # 기준
CAND = ROOT / "reports/runs/colab-1790141677344456786/dev-debug"   # B1 후보 회차


def load_script():
    spec = importlib.util.spec_from_file_location("submission", ROOT / "script.py")
    m = importlib.util.module_from_spec(spec)
    sys.modules["submission"] = m
    spec.loader.exec_module(m)
    m.load_sme_reference(str(ROOT / "open/data"))
    return m


def responses(case):
    """단계별 원응답과 company 입력 예산."""
    texts, chars = {}, {}
    for line in (case / "diagnostics.jsonl").read_text(encoding="utf-8").splitlines():
        e = json.loads(line)
        if e.get("event") == "company_size_input":
            chars[e["id"]] = e["max_chars"]
        if (e.get("event") == "response" and e.get("status") == "valid"
                and "response_text" in e and e.get("id")):
            texts.setdefault(e["phase"], {})[e["id"]] = e["response_text"]
    return texts, chars


def legacy_flags(script, case):
    """그 회차의 설정으로 파싱한다. 새 필드를 구 회차에 소급하지 않는다."""
    settings = json.loads((case / "run_report.json").read_text(encoding="utf-8"))
    settings = settings["reproduction"]["settings"]
    out = {}
    if hasattr(script, "DOCUMENT_CHECK_ITEMS") and not settings.get("company_size_document_checks"):
        out["company_size_legacy"] = True
    if hasattr(script, "CLAUSE_QUOTE_MAX"):
        out["company_size_clause_quotes"] = bool(settings.get("company_size_clause_quotes"))
    if hasattr(script, "QUALIFICATION_ROLES"):
        out["company_size_qualification_role"] = bool(settings.get("company_size_qualification_role"))
    return out


def company_facts(script, case, want=None):
    """각 공고의 company_size 사실과 밴드 게이트 사유를 뽑는다."""
    texts, chars = responses(case)
    flags = legacy_flags(script, case)
    out = {}
    for rec in script.iter_records(str(ROOT / "open/dev.jsonl")):
        identifier = rec["id"]
        if want and identifier not in want:
            continue
        text = texts.get("company_size", {}).get(identifier)
        if text is None:
            out[identifier] = {"_reason": "company 무응답"}
            continue
        focused, _ = script.parse_judgment(text, expected_items=script.COMPANY_SIZE_KEYS, **flags)
        facts = focused["company_size"]
        # 밴드 게이트가 무엇을 돌려주는지 — 이것이 v14~v18 을 가른다
        _bands, reason = script._company_size_bands(
            _normalised(script, facts, rec, chars[identifier]), rec, chars[identifier])
        out[identifier] = {**facts, "_reason": reason}
    return out


def _normalised(script, facts, rec, max_chars):
    """`verify_company_size` 가 밴드에 넘기기 전에 하는 정규화를 그대로 재현한다."""
    visible = script.build_context(rec, max_chars)
    facts = dict(facts)
    if "qualification_role" in facts:
        role = facts["qualification_role"]
        allowed = ("small_only", "sme_allowed") if role == "eligibility" else (
            ("unrestricted",) if role in ("checklist", "legal_reference", "none") else ())
        if facts.get("qualification") not in allowed:
            facts["qualification"] = "unknown"
    for key in ("scope_quote", "qualification_quote"):
        fixed = script.restore_spacing(facts.get(key), rec, visible)
        if fixed is not None:
            facts[key] = fixed
    return facts


FIELDS = ("scope", "qualification", "qualification_role", "qualification_complete",
          "priority_exception", "size_exception", "requirements_complete", "_reason")


def verdict(truth_value, predicted):
    """라벨과 예측으로 TP/FP/FN/TN 을 낸다."""
    if truth_value == predicted == "1":
        return "TP"
    if truth_value == "1":
        return "FN"
    return "FP" if predicted == "1" else "TN"


def main():
    script = load_script()
    truth = {r["id"]: r for r in csv.DictReader(open(ROOT / "open/dev_labels.csv", encoding="utf-8"))}
    if len(sys.argv) < 2:
        raise SystemExit("기준 재생 CSV 경로를 인자로 준다 (판정 당시 코드로 재생한 것)")
    base_csv = {r["id"]: r for r in csv.DictReader(open(sys.argv[1], encoding="utf-8"))}
    cand_csv = {r["id"]: r for r in csv.DictReader(open(CAND / "submission.csv", encoding="utf-8"))}

    changed = [(i, v) for i in base_csv for v in script.ITEMS if base_csv[i][v] != cand_csv[i][v]]
    focus = ["v14", "v15", "v16", "v17", "v18"]

    print(f"바뀐 셀 {len(changed)} · 대상 밖 {sum(1 for _, v in changed if v not in focus)}\n")

    print("=== 대상 밖 항목별 내역 ===")
    print(f'{"항목":<6}{"셀":>4}  공고 · 전→후 (라벨) · 방향')
    off = {}
    for i, v in changed:
        if v not in focus:
            off.setdefault(v, []).append(i)
    for v in sorted(off, key=lambda x: int(x[1:])):
        parts = []
        for i in off[v]:
            t, a, b = truth[i][v], base_csv[i][v], cand_csv[i][v]
            parts.append(f'{i.replace("PPS-DEV-", "")} {a}→{b} ({t}) '
                         f'{verdict(t, a)}→{verdict(t, b)}')
        print(f'{v:<6}{len(off[v]):>4}  ' + " · ".join(parts))

    want = {i for i, v in changed if v in focus}
    want |= {"PPS-DEV-038", "PPS-DEV-043", "PPS-DEV-127", "PPS-DEV-187"}
    print("\n=== 대상 항목에서 바뀐 공고의 사실 전→후 ===")
    b_facts = company_facts(script, BASE, want)
    c_facts = company_facts(script, CAND, want)
    for i in sorted(want, key=lambda x: (len(x), x)):
        moved = [v for v in focus if base_csv[i][v] != cand_csv[i][v]]
        bf, cf = b_facts.get(i, {}), c_facts.get(i, {})
        diff = [k for k in FIELDS if bf.get(k) != cf.get(k)]
        print(f'\n--- {i.replace("PPS-DEV-", "")} · 셀 {moved or "(대상 항목 변화 없음)"}')
        for v in moved:
            print(f'      {v}: {base_csv[i][v]} → {cand_csv[i][v]} (라벨 {truth[i][v]})')
        if not diff:
            print("      사실 동일 — 이 단계에서는 원인 불명")
        for k in diff:
            print(f'      {k:<22}{str(bf.get(k))[:46]:<48}→ {str(cf.get(k))[:46]}')


if __name__ == "__main__":
    main()
