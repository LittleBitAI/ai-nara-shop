"""A3 H1의 변경 범위와 보관 응답을 검사한다. 모델 효과를 검사하지 않는다."""

import ast
import csv
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
import script  # noqa: E402
from tools.replay_run import saved_responses  # noqa: E402

BASE = "6bb692d6162e6b604dae34e6e8044cc31dd7a60b"
CASE = "reports/runs/colab-1789880471715651259/dev-debug"


def main():
    before = subprocess.check_output(["git", "show", f"{BASE}:script.py"], cwd=ROOT)
    after = (ROOT / "script.py").read_bytes()
    trees = [ast.parse(raw.decode("utf-8")) for raw in (before, after)]
    prompts = []
    for tree in trees:
        node = next(n for n in tree.body if isinstance(n, ast.Assign)
                    and any(isinstance(t, ast.Name) and t.id == "COMPANY_SIZE_PROMPT"
                            for t in n.targets))
        prompts.append(ast.literal_eval(node.value))
        node.value = ast.Constant(value="<prompt>")
    assert ast.dump(trees[0]) == ast.dump(trees[1]), "프롬프트 외 코드 변경"
    assert prompts[0] != prompts[1], "프롬프트 변경 없음"
    for prompt in prompts:
        assert "PPS-DEV" not in prompt, "dev ID가 프롬프트에 들어갔다"
    for part in (lambda p: p.split("- qualification:")[0],
                 lambda p: p.split("- qualification_quote:")[1]):
        assert part(prompts[0]) == part(prompts[1]), "자격 문단 외 프롬프트 변경"

    texts = saved_responses(ROOT / CASE)
    records = {r["id"]: r for r in script.iter_records(str(ROOT / "open/dev.jsonl"))}
    with (ROOT / "open/dev_labels.csv").open(encoding="utf-8", newline="") as stream:
        labels = list(csv.DictReader(stream))
    assert set(texts["company_size"]) == set(records)
    cases = []
    for label in labels:
        if label["v18"] != "1":
            continue
        rec = records[label["id"]]
        facts = json.loads(texts["company_size"][rec["id"]])["company_size"]
        quote = facts["qualification_quote"]
        cases.append({"id": rec["id"], "facts": facts,
                      "exact_document_matches": [d["doc_id"] for d in rec["docs"]
                                                 if quote and quote in d["text"]],
                      "exact_metadata_matches": [k for k, v in rec["meta"].items()
                                                 if quote and quote == v]})
    assert len(cases) == 7
    assert sum("조항호내용" in c["exact_metadata_matches"] for c in cases) == 4
    metadata_quotes = []
    for rec in records.values():
        fact = json.loads(texts["company_size"][rec["id"]])["company_size"]
        quote = fact["qualification_quote"]
        if quote and quote == rec["meta"].get("조항호내용"):
            metadata_quotes.append(rec["id"])
    assert len(metadata_quotes) == 8
    # 감사 표본의 위치 검증이다. 아래 ID·기대 역할은 추론 코드/프롬프트에 전달하지 않는다.
    examples = []
    for id_, quote, role in [
        ("PPS-DEV-038", "거. 소기업 또는 소상공인확인서 1부", "checklist"),
        ("PPS-DEV-043", "12) 중·소기업, 소상공인확인서 중 1부", "checklist"),
        ("PPS-DEV-044", "① 「중소기업제품 구매촉진 및 판로지원에 관한 법률」 제8조의2에 해당하는 자",
         "statutory_exclusion"),
        ("PPS-DEV-039", "입 찰 방 법: 제한경쟁(소기업·소상공인), 총액(전자)입찰", "eligibility"),
    ]:
        doc = next(d for d in records[id_]["docs"] if quote in d["text"])
        start = doc["text"].index(quote)
        assert doc["text"][start:start + len(quote)] == quote
        examples.append(dict(id=id_, doc_id=doc["doc_id"], start=start, end=start + len(quote),
                             quote=quote, expected_role=role, model_role_tested=False))
    result = {"mode": "source_audit_only", "model_called": False, "baseline_commit": BASE,
              "case": CASE, "only_qualification_prompt_changed": True,
              "script_sha256": hashlib.sha256(after).hexdigest(),
              "prompt_sha256": [hashlib.sha256(p.encode()).hexdigest() for p in prompts],
              "all_dev_metadata_quote_ids": metadata_quotes,
              "v18_positive_cases": cases, "role_examples": examples}
    output = Path(__file__).with_name("audit.json")
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                      encoding="utf-8", newline="\n")
    print("자격 문단 외 AST 동일 · v18 양성 7건 중 메타 인용 4건 · 역할 표본 원문 4건 확인")


if __name__ == "__main__":
    main()
