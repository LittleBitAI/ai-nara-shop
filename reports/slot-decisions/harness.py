"""Load cache + labels; score a verdict function per pool, per half, with a paired bootstrap."""
import csv
import os
import tempfile
import pickle
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
# The full unlabeled input lives in the main checkout, not in worktrees; point PPS_MAIN_REPO at it.
MAIN_REPO = Path(os.environ.get("PPS_MAIN_REPO", ROOT))
# Unpacked `offdev-600-results-1790471557297701344.zip` (D's deb6831 run), and a scratch directory.
OFFDEV600 = Path(os.environ.get("OFFDEV600_DIR", ROOT / "artifacts/offdev-600-1790471557297701344"))
WORK = Path(os.environ.get("SLOT_WORK", Path(tempfile.gettempdir()) / "slot-decisions"))
WORK.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT / "reports/labels-3000"))
from pick import half  # noqa: E402

ITEMS = [f"v{i}" for i in range(1, 25)]


def read_labels(*paths):
    out = {}
    for p in paths:
        with open(p, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                out[r["id"]] = {v: (None if r[v] == "" else int(r[v])) for v in ITEMS}
    return out


def load():
    cache = pickle.load(open(WORK / "cache.pkl", "rb"))
    dev = read_labels(MAIN_REPO / "open/dev_labels.csv")
    o600 = read_labels(ROOT / "reports/labels-600/merged/diag.csv", ROOT / "reports/labels-600/merged/sealed.csv")
    l2000 = read_labels(ROOT / "reports/labels-3000/merged.csv")
    private = set((ROOT / "reports/labels-3000/private-ids.txt").read_text(encoding="utf-8").split())
    pools = {"dev": (cache["dev"], dev), "o600": (cache["o600"], o600),
             "l2000": (cache["l2000"], {i: r for i, r in l2000.items() if i not in set(o600)})}
    return pools, private


def counts(pred, truth, ids):
    c = {}
    for i in ids:
        t, p = truth[i], pred[i]
        for v in ITEMS:
            if t[v] is None:
                continue
            x = c.setdefault(v, [0, 0, 0])
            a, b = t[v], p[v]
            x[0] += a & b
            x[1] += b & (1 - a)
            x[2] += a & (1 - b)
    return c


def macro(c):
    f = [2 * tp / (2 * tp + fp + fn) if tp + fp + fn else 0.0 for tp, fp, fn in c.values()]
    return sum(f) / len(f) if f else 0.0


def f1(x):
    tp, fp, fn = x
    return 2 * tp / (2 * tp + fp + fn) if tp + fp + fn else 0.0


def verdicts(entries, fn):
    return {i: fn(e) for i, e in entries.items()}


def current(e):
    return {v: int(e["final"][v]["위반여부"]) for v in ITEMS}


def bootstrap(pred_a, pred_b, truth, ids, n=2000, seed=7):
    """P(macro(b) > macro(a)) over notice resamples, and the 5th percentile of the delta."""
    ids = list(ids)
    rng = random.Random(seed)
    # per-notice per-item contributions
    rows = []
    for i in ids:
        t = truth[i]
        ra, rb = [], []
        for k, v in enumerate(ITEMS):
            if t[v] is None:
                ra.append(None)
                rb.append(None)
                continue
            a, x, y = t[v], pred_a[i][v], pred_b[i][v]
            ra.append((a & x, x & (1 - a), a & (1 - x)))
            rb.append((a & y, y & (1 - a), a & (1 - y)))
        rows.append((ra, rb))
    deltas = []
    for _ in range(n):
        sa = [[0, 0, 0] for _ in ITEMS]
        sb = [[0, 0, 0] for _ in ITEMS]
        seen = [False] * len(ITEMS)
        for _ in range(len(rows)):
            ra, rb = rows[rng.randrange(len(rows))]
            for k in range(len(ITEMS)):
                if ra[k] is None:
                    continue
                seen[k] = True
                for j in range(3):
                    sa[k][j] += ra[k][j]
                    sb[k][j] += rb[k][j]
        ks = [k for k in range(len(ITEMS)) if seen[k]]
        ma = sum(f1(sa[k]) for k in ks) / len(ks)
        mb = sum(f1(sb[k]) for k in ks) / len(ks)
        deltas.append(mb - ma)
    deltas.sort()
    return sum(d > 0 for d in deltas) / n, deltas[int(0.05 * n)], sum(deltas) / n


def report(pools, private, fn, base=current, name="cand", boot=False):
    out = {}
    for pool, (entries, truth) in pools.items():
        ids = [i for i in truth if i in entries]
        if pool != "dev":
            ids = [i for i in ids if i not in private]
        pa, pb = verdicts({i: entries[i] for i in ids}, base), verdicts({i: entries[i] for i in ids}, fn)
        ca, cb = counts(pa, truth, ids), counts(pb, truth, ids)
        row = {"n": len(ids), "base": round(macro(ca), 4), name: round(macro(cb), 4)}
        if pool != "dev":
            for h in "AB":
                hid = [i for i in ids if half(i) == h]
                row[f"d{h}"] = round(macro(counts(pb, truth, hid)) - macro(counts(pa, truth, hid)), 4)
        moved = {v: (ca[v], cb[v]) for v in cb if ca[v] != cb[v]}
        row["moved"] = {v: f"{a[0]}/{a[1]}/{a[2]}->{b[0]}/{b[1]}/{b[2]}" for v, (a, b) in moved.items()}
        if boot:
            row["P>0"], row["q05"], row["mean"] = [round(x, 4) for x in bootstrap(pa, pb, truth, ids)]
        out[pool] = row
    return out
