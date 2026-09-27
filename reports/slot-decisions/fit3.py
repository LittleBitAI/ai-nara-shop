"""Four-slot templates per item: raise = applies & requirement & not-exception & observed; drop = cur where
applies fails. Every option is read off the item definition. Nested cross-fit over halves of off-dev AND dev.
"""
import itertools
import json
import pickle
import random

import numpy as np

import harness as h
from fit import literal, f1

T = "T"
GEN = ["cs_scope=general", "!competitive_by_codes=True", "cs_scope=general&!competitive_by_codes=True", T]
COMP = ["cs_scope=competitive", "competitive_by_codes=True", "cs_scope=competitive&!outside_catalogue&!catalogue_miss",
        "cs_scope=competitive|competitive_by_codes=True"]
NO_EXC = [T, "!cs_priority_exception=yes", "cs_priority_exception=no"]
OBS = [T, "complete", "cs_qualification_complete=yes", "cs_requirements_complete=yes"]
UNLIMITED = ["cs_qualification=unrestricted", "!size_limited", "cs_qualification=unrestricted&!size_limited",
             "cs_qualification_role=checklist|cs_qualification_role=none|cs_qualification_role=legal_reference",
             "cs_qualification=unrestricted|cs_qualification_role=checklist"]

# item: (applies options, requirement options, exception options, observed options, drop-if-not options)
TEMPLATES = {
    "v2": (["lo", "small", "lo&!local_small_quote", "small&!local_small_quote"],
           ["m_v2", "m_v3", "m_v8", "perf_clause", "m_v2|m_v3", "m_v2|m_v8", "m_v3|m_v8", "m_v2|m_v3|m_v8"],
           [T], [T], [None, "lo"]),
    "v5": (["hi"], ["m_v5", "m_v6", "m_v7", "m_v8", "v5_raise", "m_v5|m_v6", "m_v6|m_v7", "m_v5|m_v6|m_v7"],
           [T], [T], [None, "hi"]),
    "v7": (["lo"], ["m_v7", "v7_detect", "m_v7|v7_detect", "m_v5&m_v7"], [T], [T], [None, "lo"]),
    "v8": ([T], ["m_v3&m_v5", "m_v3&m_v6", "m_v2&m_v5", "m_v2&m_v6", "m_v2&m_v7", "perf_clause&m_v6",
                 "perf_clause&m_v5", "m_v8&v8_detect"], [T], [T], [None]),
    "v10": (COMP, ["!dp_demand", "!cs_has_direct_production_quote", "!dp_demand&!cs_has_direct_production_quote"],
            [T], OBS, [None, "cs_scope=competitive|competitive_by_codes=True", "!outside_catalogue"]),
    "v11": (COMP, UNLIMITED, NO_EXC, OBS, [None, "cs_scope=competitive|competitive_by_codes=True", "!size_limited"]),
    "v12": (["cs_scope=general", "!competitive_by_codes=True", "cs_scope=general&!competitive_by_codes=True"],
            ["dp_demand", "cs_has_direct_production_quote", "dp_demand&cs_has_direct_production_quote"],
            [T], [T], [None, "!competitive_by_codes=True"]),
    "v14": (["hi&" + g if g != T else "hi" for g in GEN],
            ["cs_qualification=small_only|cs_qualification=sme_allowed", "size_limited",
             "cs_qualification_role=eligibility"], [T], [T], [None, "hi"]),
    "v15": (["mid&" + g if g != T else "mid" for g in GEN],
            ["cs_qualification=small_only", "cs_qualification=small_only&size_limited"],
            [T, "!cs_size_exception=joint_small"], [T], [None, "mid"]),
    "v16": (["mid&" + g if g != T else "mid" for g in GEN], UNLIMITED, NO_EXC, OBS, [None, "mid"]),
    "v17": (["small&" + g if g != T else "small" for g in GEN] + ["small&goods&cs_scope=general"],
            ["cs_qualification=sme_allowed", "cs_qualification=sme_allowed&size_limited", "m_v17&size_limited"],
            [T, "!cs_size_exception=broaden_sme"], [T], [None, "small", "size_limited"]),
    "v18": (["small&" + g if g != T else "small" for g in GEN] + ["small&goods&cs_scope=general"],
            UNLIMITED, NO_EXC, OBS, [None, "small"]),
    "v20": (["cs_software_business=yes", "sw_missing=True|sw_missing=False", "cs_software_business=yes&!sw_missing=None"],
            ["!cs_has_software_participation_quote", "sw_missing=True", "v20_dec=1",
             "!cs_has_software_participation_quote&!v20_dec=0"], [T], OBS, [None, "!v20_dec=0"]),
}


def expr(M, text, n):
    """a&b|c&!d — OR of ANDs."""
    if text is None or text == T:
        return np.ones(n, bool)
    out = np.zeros(n, bool)
    for conj in text.split("|"):
        m = np.ones(n, bool)
        for lit in conj.split("&"):
            if lit == T:
                continue
            m &= ~M[lit[1:]] if lit.startswith("!") else M[lit]
        out |= m
    return out


def lits(item):
    names = set()
    for opts in TEMPLATES[item]:
        for o in opts:
            if o:
                for conj in o.split("|"):
                    for lit in conj.split("&"):
                        if lit != T:
                            names.add(lit.lstrip("!"))
    return names


def rules(item):
    a, r, x, o, d = TEMPLATES[item]
    yield None
    for combo in itertools.product(a, r, x, o, d):
        yield combo
    for dd in d:
        if dd:
            yield (None, None, None, None, dd)


def predict(rule, M, cur):
    if rule is None:
        return cur
    a, r, x, o, d = rule
    n = len(cur)
    keep = cur & expr(M, d, n) if d else cur
    if a is None:
        return keep
    return keep | (expr(M, a, n) & expr(M, r, n) & expr(M, x, n) & expr(M, o, n))


def build(pools, private, slot, item):
    names = lits(item)
    def mats(keys, src):
        return {nm: np.array([literal(src[k], nm) for k in keys]) for nm in names}
    off = [("o600", i) for i in pools["o600"][1] if i not in private] + \
          [("l2000", i) for i in pools["l2000"][1] if i not in private]
    off = [k for k in off if pools[k[0]][1][k[1]][item] is not None]
    Mo = {nm: np.array([literal(slot[k[0]][k[1]], nm) for k in off]) for nm in names}
    yo = np.array([pools[k[0]][1][k[1]][item] == 1 for k in off])
    co = np.array([slot[k[0]][k[1]]["c_" + item] for k in off])
    ho = np.array([h.half(k[1]) for k in off])
    dev = list(pools["dev"][1])
    Md = mats(dev, slot["dev"])
    yd = np.array([pools["dev"][1][i][item] == 1 for i in dev])
    cd = np.array([slot["dev"]["c_" + item] if False else slot["dev"][i]["c_" + item] for i in dev])
    hd = np.array([h.half(i) for i in dev])
    return (Mo, yo, co, ho, off), (Md, yd, cd, hd, dev)


def sub(M, m):
    return {k: v[m] for k, v in M.items()}


def select(item, O, D, mo, md, margin):
    """Best rule on the masked off-dev rows, feasible if it gains > margin there and dev does not fall."""
    Mo, yo, co = O[0], O[1], O[2]
    Md, yd, cd = D[0], D[1], D[2]
    Mo, yo, co = sub(Mo, mo), yo[mo], co[mo]
    Md, yd, cd = sub(Md, md), yd[md], cd[md]
    bo, bd = f1(yo, co)[0], f1(yd, cd)[0]
    best = (margin, None)
    for rule in rules(item):
        if rule is None:
            continue
        g = f1(yo, predict(rule, Mo, co))[0] - bo
        if g <= best[0]:
            continue
        if f1(yd, predict(rule, Md, cd))[0] < bd:
            continue
        best = (g, rule)
    return best[1]


def main(margin=0.02):
    pools, private = h.load()
    slot = pickle.load(open(h.WORK / "slots.pkl", "rb"))
    report = {}
    for item in TEMPLATES:
        O, D = build(pools, private, slot, item)
        ho, hd = O[3], D[3]
        cross = {}
        for fit_h, test_h in (("A", "B"), ("B", "A")):
            rule = select(item, O, D, ho == fit_h, hd == fit_h, margin)
            mo, md = ho == test_h, hd == test_h
            po = predict(rule, sub(O[0], mo), O[2][mo]); pd = predict(rule, sub(D[0], md), D[2][md])
            cross[fit_h] = {"rule": rule,
                            "off": f"{f1(O[1][mo], O[2][mo])[1]}->{f1(O[1][mo], po)[1]}",
                            "d_off": round(f1(O[1][mo], po)[0] - f1(O[1][mo], O[2][mo])[0], 3),
                            "dev": f"{f1(D[1][md], D[2][md])[1]}->{f1(D[1][md], pd)[1]}",
                            "d_dev": round(f1(D[1][md], pd)[0] - f1(D[1][md], D[2][md])[0], 3)}
        full = select(item, O, D, np.ones(len(ho), bool), np.ones(len(hd), bool), margin)
        po, pd = predict(full, O[0], O[2]), predict(full, D[0], D[2])
        report[item] = {"cross": cross, "full_rule": full,
                        "full_off": f"{f1(O[1], O[2])[1]}->{f1(O[1], po)[1]} {f1(O[1], po)[0] - f1(O[1], O[2])[0]:+.3f}",
                        "full_dev": f"{f1(D[1], D[2])[1]}->{f1(D[1], pd)[1]} {f1(D[1], pd)[0] - f1(D[1], D[2])[0]:+.3f}"}
        print(item, json.dumps(report[item], ensure_ascii=False), flush=True)
    json.dump(report, open(h.WORK / "fit3.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    import sys
    main(*(float(a) for a in sys.argv[1:2]))
