"""Replay current script.py over every labelled pool, keeping the intermediate facts per notice.

Output: cache.pkl = {pool: {id: {"rec", "main", "p1", "company", "company_verified", "sme", "final"}}}
"""
import json
import pickle
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from harness import ROOT, MAIN_REPO, OFFDEV600, WORK
sys.path.insert(0, str(ROOT / "tools"))
import replay_run  # noqa: E402

script = replay_run.load_module(ROOT / "script.py", "submission")

UNL = ROOT / "reports/label-compare/unlabeled-d"
CASES = {
    "dev": [(ROOT / "reports/runs/colab-1790432295199698396/dev-debug", None)],
    "o600": [(OFFDEV600 / "drive/u00/output", OFFDEV600 / "drive/u00/ids.json"),
             (OFFDEV600 / "drive/u01/output", OFFDEV600 / "drive/u01/ids.json")],
    "l2000": [(d / "output", d / "ids.json") for run in sorted(UNL.glob("run-*"))
              for d in sorted(run.glob("u*")) if d.name != "u11"],
}


def unlabeled_index(wanted):
    out = {}
    with open(MAIN_REPO / "open/train_unlabeled.jsonl", encoding="utf-8") as stream:
        for line in stream:
            head = line[:60]
            i = head.find('"id"')
            rid = json.loads(line)["id"] if i < 0 else None
            if rid is None:
                rid = line.split('"id"', 1)[1].split('"', 2)[1]
            if rid in wanted:
                out[rid] = line
    return out


def main():
    cache = {}
    for pool, cases in CASES.items():
        got = {}
        for case, ids_file in cases:
            if ids_file is None:
                input_path = MAIN_REPO / "open/dev.jsonl"
            else:
                ids = json.loads(Path(ids_file).read_text(encoding="utf-8"))
                lines = unlabeled_index(set(ids))
                input_path = WORK / f"in-{pool}-{case.parent.parent.name}-{case.parent.name}.jsonl"
                input_path.write_text("".join(lines[i] for i in ids), encoding="utf-8")
            captured = {}

            def post(parsed, rec, _c=captured):
                final = script.postprocess(parsed, rec)
                _c[rec["id"]] = {"rec": rec, "parsed": json.loads(json.dumps(parsed, ensure_ascii=False)),
                                 "final": final}
                return final

            def vcs(facts, rec, max_chars, _c=captured):
                out, reason = script.verify_company_size(facts, rec, max_chars)
                _c.setdefault("__company", {})[rec["id"]] = {"facts": dict(facts), "verified": out,
                                                              "reason": reason, "max_chars": max_chars}
                return out, reason

            # main verdicts before sme/company merge: wrap parse via baseline_rows? replay keeps parsed
            # mutated; capture the pure main-call verdicts from the saved text separately.
            result = replay_run.replay(script, case, input_path=input_path,
                                       data_dir=ROOT / "open/data", postprocess=post,
                                       verify_company_size=vcs)
            texts = replay_run.saved_responses(case)
            probs = replay_run.saved_probabilities(case)
            company = captured.pop("__company", {})
            for rid, c in captured.items():
                main_parsed, _ = script.parse_judgment(texts["baseline"][rid])
                c["main"] = main_parsed
                c["p1"] = probs.get(rid)
                c["company"] = company.get(rid)
                got[rid] = c
            print(pool, case, len(captured), flush=True)
        cache[pool] = got
    with open(WORK / "cache.pkl", "wb") as f:
        pickle.dump(cache, f)


if __name__ == "__main__":
    main()
