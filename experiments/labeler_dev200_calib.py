"""Per-item labeler vs dev gold, with the preset verdict from dev200/README.md."""
import csv, glob, json
V = [f"v{i}" for i in range(1, 25)]
gold = {r["id"]: r for r in csv.DictReader(open("open/dev_labels.csv", encoding="utf-8"))}
model = {r["id"]: r for r in csv.DictReader(open(
    "reports/runs/colab-1790081509639025520/dev/submission.csv", encoding="utf-8"))}
lab = {}
for f in sorted(glob.glob("reports/label-compare/dev200/*.jsonl")):
    for line in open(f, encoding="utf-8"):
        if line.strip():
            r = json.loads(line)
            assert r["id"] not in lab, r["id"]
            lab[r["id"]] = r["labels"]
ids = sorted(lab)
print(f"labelled {len(ids)}/200")

def f1(tp, fp, fn):
    return 2 * tp / (2 * tp + fp + fn) if tp + fp + fn else 0.0

print("| item | pos | TP | FP | FN | labeler F1 | sens | FP rate | model F1 | verdict |")
print("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |")
tot = {"trust": 0, "cond": 0, "drop": 0}
for v in V:
    tp = fp = fn = mtp = mfp = mfn = 0
    for i in ids:
        g = int(gold[i][v] or 0)
        p = int(lab[i][v]["위반여부"])
        m = int(model[i][v] or 0)
        tp += g & p; fp += (1 - g) & p; fn += g & (1 - p)
        mtp += g & m; mfp += (1 - g) & m; mfn += g & (1 - m)
    F = f1(tp, fp, fn)
    verdict = "trust" if F >= 0.80 else "cond" if F >= 0.60 else "drop"
    tot[verdict] += 1
    neg = len(ids) - tp - fn
    border = " (edge)" if abs(F - 0.80) < 0.08 or abs(F - 0.60) < 0.08 else ""
    print(f"| {v} | {tp+fn} | {tp} | {fp} | {fn} | {F:.3f} | {tp/(tp+fn) if tp+fn else 0:.2f} "
          f"| {fp/neg if neg else 0:.3f} | {f1(mtp,mfp,mfn):.3f} | {verdict}{border} |")
print(tot)
