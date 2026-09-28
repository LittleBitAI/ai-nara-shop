"""Per item, search `(cur and not drop) or (applies and evidence)` over the slots its definition names.

Cross-fit: pick on half A, score on half B, and the reverse. An item changes only when both directions gain.
"""
import itertools
import json
import pickle
import sys

import numpy as np

import harness as h

THRESHOLDED = {"v1", "v3", "v4", "v6", "v9", "v22", "v23", "v24"}
PERF = ["m_v2", "m_v3", "m_v4", "m_v8", "perf_clause", "v8_detect", "v4_detect"]
REGION = ["m_v5", "m_v6", "m_v7", "m_v8", "v5_raise", "v6_raise", "v7_detect"]
SIZE = ["cs_qualification=small_only", "cs_qualification=sme_allowed", "cs_qualification=unrestricted",
        "cs_qualification=unknown", "cs_qualification_role=eligibility", "cs_qualification_role=checklist",
        "cs_qualification_role=none", "cs_qualification_role=legal_reference", "size_limited", "sme_allowed_text"]
SCOPE = ["cs_scope=general", "cs_scope=competitive", "cs_scope=other", "competitive_by_codes=True",
         "competitive_by_codes=False", "outside_catalogue", "catalogue_miss", "goods"]
OBS = ["complete", "cs_qualification_complete=yes", "cs_requirements_complete=yes"]
EXC = ["cs_priority_exception=yes", "cs_priority_exception=no", "cs_size_exception=none"]
BAND = ["lo", "hi", "mid", "small", "local_small_quote"]
REASON = ["cs_reason=decided", "cs_reason=unverified_qualification", "cs_reason=unverified_priority_exception",
          "cs_reason=absence_not_observable", "cs_reason=outside_general_scope", "cs_reason=unverified_scope"]

GROUND = {
    "v2": BAND + PERF,
    "v5": BAND + REGION,
    "v7": BAND + REGION,
    "v8": PERF + REGION,
    "v10": SCOPE + ["dp_demand", "cs_has_direct_production_quote", "m_v10", "cv_v10", "m_v12"] + OBS,
    "v11": SCOPE + SIZE + OBS + EXC + ["m_v11", "cv_v11", "m_v10"],
    "v12": SCOPE + ["dp_demand", "cs_has_direct_production_quote", "m_v12", "cv_v12"],
    "v13": SCOPE + SIZE + ["m_v13"],
    "v14": BAND + SCOPE + SIZE + ["m_v14", "cv_v14"] + REASON,
    "v15": BAND + SCOPE + SIZE + ["m_v15", "cv_v15"] + REASON,
    "v16": BAND + SCOPE + SIZE + OBS + EXC + ["m_v16", "cv_v16"] + REASON,
    "v17": BAND + SCOPE + SIZE + ["m_v17", "cv_v17", "m_v18"] + REASON,
    "v18": BAND + SCOPE + SIZE + OBS + EXC + ["m_v18", "cv_v18", "m_v17", "dp_demand"] + REASON,
    "v19": ["m_v19", "v19_bid"],
    "v20": ["cs_software_business=yes", "cs_software_business=no", "cs_has_software_participation_quote",
            "sw_missing=True", "sw_missing=False", "v20_dec=1", "v20_dec=0", "m_v20"] + OBS,
    "v21": ["m_v21"],
}


def literal(slots, name):
    if "=" in name:
        key, val = name.split("=", 1)
        return str(slots.get(key)) == val
    return bool(slots.get(name))


def matrices(pool_slots, ids, names):
    return {n: np.array([literal(pool_slots[i], n) for i in ids]) for n in names}


def f1(y, p):
    tp = int((y & p).sum()); fp = int((~y & p).sum()); fn = int((y & ~p).sum())
    return (2 * tp / (2 * tp + fp + fn) if tp + fp + fn else 0.0), (tp, fp, fn)


def candidates(item, M, cur):
    """Yield (description, prediction)."""
    names = [n for n in GROUND[item] if n in M]
    lits = [(n, M[n]) for n in names] + [("!" + n, ~M[n]) for n in names]
    true = np.ones_like(cur)
    yield ("keep",), cur
    # raise: cur or (a and e) / (a and e and g)
    for (an, a), (en, e) in itertools.product([("T", true)] + lits, lits):
        if an == en:
            continue
        yield ("raise", an, en), cur | (a & e)
    # drop: cur and not (a and d)
    for (an, a), (dn, d) in itertools.product([("T", true)] + lits, lits):
        if an == dn:
            continue
        yield ("drop", an, dn), cur & ~(a & d)


def apply_rule(rule, M, cur):
    true = np.ones_like(cur)
    def lit(n):
        return true if n == "T" else (~M[n[1:]] if n.startswith("!") else M[n])
    if rule[0] == "keep":
        return cur
    if rule[0] == "raise":
        return cur | (lit(rule[1]) & lit(rule[2]))
    return cur & ~(lit(rule[1]) & lit(rule[2]))


def best(item, M, cur, y, margin):
    base, _ = f1(y, cur)
    top = (base + margin, ("keep",))
    for rule, pred in candidates(item, M, cur):
        score, _ = f1(y, pred)
        if score > top[0]:
            top = (score, rule)
    return top[1]


def main(margin=0.02, rounds=2):
    pools, private = h.load()
    slot = pickle.load(open(h.WORK / "slots.pkl", "rb"))
    # fitting pool: off-dev, not 수의계약-private
    ids = [("o600", i) for i in pools["o600"][1] if i not in private] + \
          [("l2000", i) for i in pools["l2000"][1] if i not in private]
    S = {k: slot[k[0]][k[1]] for k in ids}
    T = {k: pools[k[0]][1][k[1]] for k in ids}
    halves = np.array([h.half(k[1]) for k in ids])
    names = sorted({n for g in GROUND.values() for n in g})
    M = {n: np.array([literal(S[k], n) for k in ids]) for n in names}
    dev_ids = list(pools["dev"][1])
    Md = {n: np.array([literal(slot["dev"][i], n) for i in dev_ids]) for n in names}
    out = {}
    for item in GROUND:
        if item in THRESHOLDED:
            continue
        lab = np.array([T[k][item] is not None for k in ids])
        y = np.array([T[k][item] == 1 for k in ids])
        cur = np.array([S[k]["c_" + item] for k in ids])
        res = {}
        for fit_h, test_h in (("A", "B"), ("B", "A")):
            fm, tm = (halves == fit_h) & lab, (halves == test_h) & lab
            rule = best(item, {n: v[fm] for n, v in M.items()}, cur[fm], y[fm], margin)
            b, bc = f1(y[tm], cur[tm])
            a, ac = f1(y[tm], apply_rule(rule, {n: v[tm] for n, v in M.items()}, cur[tm]))
            res[fit_h] = {"rule": rule, "test_delta": round(a - b, 4), "test": f"{bc}->{ac}"}
        full_rule = best(item, {n: v[lab] for n, v in M.items()}, cur[lab], y[lab], margin)
        yd = np.array([pools["dev"][1][i][item] == 1 for i in dev_ids])
        curd = np.array([slot["dev"][i]["c_" + item] for i in dev_ids])
        db, dbc = f1(yd, curd)
        da, dac = f1(yd, apply_rule(full_rule, Md, curd))
        fb, fbc = f1(y[lab], cur[lab])
        fa, fac = f1(y[lab], apply_rule(full_rule, {n: v[lab] for n, v in M.items()}, cur[lab]))
        out[item] = {"A->B": res["A"], "B->A": res["B"], "full_rule": full_rule,
                     "full": f"{fbc}->{fac} {fb:.3f}->{fa:.3f}", "dev": f"{dbc}->{dac} {db:.3f}->{da:.3f}"}
        print(item, json.dumps(out[item], ensure_ascii=False), flush=True)
    json.dump(out, open(h.WORK / "fit.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main(*(float(a) for a in sys.argv[1:2]))
