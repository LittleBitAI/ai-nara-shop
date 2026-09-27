"""Measure per-item logprob cuts from a saved-response labelled run. No model calls.

Every labelled item except v9/v24 is searched over GRID plus "no cut" (None: the argmax answer).
Macro is over the labelled items; halves are the fixed `half(id)` of reports/labels-3000/pick.py."""
import argparse, csv, importlib.util, json, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "reports" / "labels-3000"))
from pick import half  # noqa: E402
GRID = (0.01, 0.02, 0.05, 0.1, 0.2, 0.3, 0.4, 0.6, 0.7, 0.8, 0.9, 0.95, 0.98, 0.99, 0.999)
FIXED = ("v9", "v24")  # no off-dev labels; their cuts stay as they are
TRUSTED = ("v1", "v2", "v3", "v5", "v6", "v7", "v8", "v12", "v13", "v14", "v15", "v19", "v21", "v22", "v23")

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

def score(rows, truth, items):
    out = {}
    for item in items:
        pairs = [(int(r[item]), truth[r["id"]][item]) for r in rows if truth[r["id"]][item] in ("0", "1")]
        tp=sum(p and t=="1" for p,t in pairs); fp=sum(p and t=="0" for p,t in pairs); fn=sum(not p and t=="1" for p,t in pairs)
        out[item]={"tp":tp,"fp":fp,"fn":fn,"f1":2*tp/(2*tp+fp+fn) if tp+fp+fn else 0.0,"n":len(pairs)}
    return out

def macro(x): return sum(v["f1"] for v in x.values()) / len(x)
def on(rows, h): return [r for r in rows if half(r["id"])==h]

def main():
    p=argparse.ArgumentParser(); p.add_argument("--case",required=True); p.add_argument("--input",required=True); p.add_argument("--truth",required=True); p.add_argument("--out",required=True); a=p.parse_args()
    out=Path(a.out); out.mkdir(parents=True,exist_ok=False)
    replay=load("replay_run",ROOT/"tools/replay_run.py"); script=load("submission",ROOT/"script.py")
    truth={r["id"]:r for r in csv.DictReader(Path(a.truth).open(encoding="utf-8",newline=""))}; records=list(script.iter_records(a.input)); ids=[r["id"] for r in records]
    if set(ids)!=set(truth) or len(ids)!=len(truth): raise SystemExit("input과 truth ID 집합/건수가 다르다")
    original=dict(script.ITEM_THRESHOLDS); labelled=[i for i in script.ITEMS if any(truth[x][i] in ("0","1") for x in ids)]; eligible=[i for i in labelled if i not in FIXED]
    fixed={i:x for i,x in original.items() if i not in eligible}; grid=[None]+sorted(set(GRID)|{original[i] for i in eligible if i in original})
    # Every searched item needs P(1) on every notice, or apply_thresholds() silently keeps argmax for it.
    probs=replay.saved_probabilities(a.case); short=[x for x in ids if not set(eligible)<=set(probs.get(x) or {})]
    if short: raise SystemExit(f"{len(short)} of {len(ids)} notices lack item_p1 for a searched item, e.g. {short[:3]}")
    def cuts(c): return {**fixed,**({} if c is None else {i:c for i in eligible})}
    def run(path, cuts):
        script.ITEM_THRESHOLDS.clear(); script.ITEM_THRESHOLDS.update(cuts)
        expected=[r["id"] for r in script.iter_records(path)]
        return replay.replay(script,a.case,input_path=path,data_dir=str(ROOT/"open/data"),expected_ids=expected)["rows"]
    def choose(gridrows, base, labels, guard=False):
        base_s=score(base,labels,eligible); selected={}
        for item in eligible:
            best=(base_s[item]["f1"],original.get(item))
            for cut,rows in gridrows.items():
                f=score(rows,labels,(item,))[item]["f1"]
                # guard: the full-pool cut must itself beat the baseline on half A and on half B.
                ok=not guard or all(score(on(rows,h),labels,(item,))[item]["f1"]>score(on(base,h),labels,(item,))[item]["f1"]+1e-12 for h in ("A","B"))
                if ok and f>best[0]+1e-12: best=(f,cut)
            selected[item]=best[1]
        return {**fixed,**{i:c for i,c in selected.items() if c is not None}}
    try:
        base=run(a.input,original); allgrid={c:run(a.input,cuts(c)) for c in grid}; chosen=choose(allgrid,base,truth,guard=True); candidate=run(a.input,chosen)
        bscore,cscore=score(base,truth,labelled),score(candidate,truth,labelled); halves={}
        with tempfile.TemporaryDirectory(prefix="threshold-halves-") as tmp:
            for h in ("A","B"):
                train=[r for r in records if half(r["id"])==h]; test=[r for r in records if half(r["id"])!=h]
                paths=[]
                for name, rows in (("train",train),("test",test)):
                    path=Path(tmp)/f"{name}-{h}.jsonl"; path.write_text("".join(json.dumps(r,ensure_ascii=False)+"\n" for r in rows),encoding="utf-8",newline="\n"); paths.append(path)
                train_truth={r["id"]:truth[r["id"]] for r in train}; test_truth={r["id"]:truth[r["id"]] for r in test}
                trainbase=run(paths[0],original); traingrid={c:run(paths[0],cuts(c)) for c in grid}; hcuts=choose(traingrid,trainbase,train_truth)
                testbase=run(paths[1],original); testcandidate=run(paths[1],hcuts)
                halves[h]={"train_n":len(train),"test_n":len(test),"chosen":hcuts,"test_base_macro":macro(score(testbase,test_truth,labelled)),"test_candidate_macro":macro(score(testcandidate,test_truth,labelled))}
        final={h:{"base_macro":macro(score(on(base,h),truth,labelled)),"candidate_macro":macro(score(on(candidate,h),truth,labelled))} for h in ("A","B")}
        net={i:(cscore[i]["tp"]-cscore[i]["fp"])-(bscore[i]["tp"]-bscore[i]["fp"]) for i in TRUSTED}
        result={"purpose":"offdev_logprob_threshold_measurement","model_called":False,"case":a.case,"input":a.input,"truth":a.truth,"notices":len(ids),"labelled_items":labelled,"eligible_items":eligible,"fixed_items":fixed,"grid":grid,"baseline_thresholds":original,"chosen_thresholds":chosen,"baseline_macro":macro(bscore),"candidate_macro":macro(cscore),"per_item":{i:{"baseline":bscore[i],"candidate":cscore[i]} for i in labelled},"trusted_net_tp_minus_fp_delta":net,"split_half":halves,"final_by_half":final,"split_half_pass":all(x["test_candidate_macro"]>x["test_base_macro"] for x in halves.values()) and all(x["candidate_macro"]>x["base_macro"] for x in final.values()),"trusted_guard_pass":all(x>=-1 for x in net.values())}
        (out/"thresholds.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8",newline="\n")
        print(json.dumps({k:result[k] for k in ("baseline_macro","candidate_macro","chosen_thresholds","split_half_pass","trusted_guard_pass")},ensure_ascii=False))
    finally:
        script.ITEM_THRESHOLDS.clear(); script.ITEM_THRESHOLDS.update(original)
if __name__=="__main__": main()
