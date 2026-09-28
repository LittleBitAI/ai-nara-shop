"""Per-notice relation slots from what a server run already has: record, main call, company-size facts."""
import pickle
import sys
from pathlib import Path

import harness as h

ROOT = h.ROOT
sys.path.insert(0, str(ROOT / "tools"))
import replay_run  # noqa: E402

S = replay_run.load_module(ROOT / "script.py", "submission")
S.load_sme_reference(str(ROOT / "open/data"))


def safe(fn, *a):
    try:
        return fn(*a)
    except Exception:
        return None


def slots(e):
    rec = e["rec"]
    meta = rec.get("meta") or {}
    price = S.estimated_price(rec)
    f = {}
    f["nobid"] = meta.get("계약방법") == "수의계약"
    f["nego"] = "협상" in str(meta.get("계약방법") or "")
    f["goods"] = str(meta.get("업무구분") or "물품").startswith("물품")
    f["price_known"] = price is not None
    f["lo"] = price is not None and price < S.NOTICE_AMOUNT_WON
    f["hi"] = price is not None and price >= S.NOTICE_AMOUNT_WON
    f["mid"] = price is not None and S.SME_BAND_FLOOR_WON <= price < S.NOTICE_AMOUNT_WON
    f["small"] = price is not None and price < S.SME_BAND_FLOOR_WON
    f["local_small_quote"] = bool(safe(S.local_small_quote, rec))
    for v in h.ITEMS:
        f["m_" + v] = (e["main"].get(v) or {}).get("위반여부") == 1
        f["c_" + v] = int(e["final"][v]["위반여부"]) == 1
    c = e.get("company") or {}
    facts = c.get("facts") or {}
    f["cs_call"] = bool(c)
    f["cs_reason"] = c.get("reason")
    for k in ("scope", "qualification", "qualification_role", "qualification_complete", "requirements_complete",
              "priority_exception", "size_exception", "software_business"):
        f["cs_" + k] = facts.get(k)
    for k in ("direct_production_quote", "software_participation_quote", "qualification_quote", "scope_quote"):
        f["cs_has_" + k] = bool(facts.get(k))
    for v, cell in (c.get("verified") or {}).items():
        f["cv_" + v] = cell["위반여부"] == 1
        f["cv0_" + v] = cell["위반여부"] == 0
    # text relations
    f["perf_clause"] = safe(S.v2_performance_clause, rec) is not None
    f["size_limited"] = bool(safe(S.size_limited, rec))
    f["v5_raise"] = safe(S.v5_should_raise, rec) is not None
    f["v6_raise"] = safe(S.v6_should_raise, rec) is not None
    f["v8_detect"] = safe(S.detect, rec) is not None
    f["v7_detect"] = safe(S.detect_region_expansion, rec) is not None
    f["v4_detect"] = safe(S.detect_institution_performance, rec) is not None
    f["sw_missing"] = safe(S.sw_participation_missing, rec)
    f["v20_dec"] = safe(S.v20_decision, rec)
    f["v19_bid"] = bool(safe(S.v19_demanded_at_bid_stage, rec))
    f["catalogue_miss"] = bool(safe(S.catalogue_miss, rec))
    f["outside_catalogue"] = bool(safe(S.outside_catalogue, rec))
    demand, codes = S.direct_production_demand(rec)
    f["dp_demand"] = demand is not None
    f["competitive_by_codes"] = safe(S.competitive_product, rec, codes)
    f["sme_allowed_text"] = bool(S.SME_ALLOWED.search(S.build_context(rec, max_chars=S.PROMPT_BUDGET)))
    f["complete"] = (rec.get("input_completeness", {}).get("완전관측") is True
                     and not any((rec.get("dropped_doc_counts") or {}).values()))
    return f


def main():
    pools, private = h.load()
    out = {}
    for pool, (entries, truth) in pools.items():
        out[pool] = {i: slots(entries[i]) for i in truth if i in entries}
        print(pool, len(out[pool]), flush=True)
    pickle.dump(out, open(h.WORK / "slots.pkl", "wb"))


if __name__ == "__main__":
    main()
