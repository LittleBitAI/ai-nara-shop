"""후보 규칙이 발화한 사례를 사람이 읽을 수 있게 뽑는다. 모델을 부르지 않는다.

왜 필요한가. 규칙은 공개 dev 200건을 보고 만들었고 저장소에 다른 라벨 세트가 없다.
그래서 일반화 여부를 수치로 검증할 방법이 없고 사람이 근거 문구를 읽는 수밖에 없다.
이 도구는 발화한 공고마다 규칙이 근거로 삼은 원문을 그대로 꺼내 표로 만든다.

정답은 대조 표시에만 쓰고 판정에는 쓰지 않는다.
"""

import argparse
import csv
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read_labels(path):
    if not path or not Path(path).is_file():
        return {}
    with open(path, encoding="utf-8", newline="") as stream:
        return {row["id"]: row for row in csv.DictReader(stream)}


def firings(candidate, records, items):
    for rec in records:
        for item in items:
            rule = candidate.RULES.get(item)
            if rule is None:
                continue
            hit = rule(rec)
            if hit:
                yield rec, item, hit


def suppressed(candidate, records):
    """가드가 막은 사례. 가드가 틀리면 여기서 정답 양성을 잃는다.

    막힌 자리가 가장 위험하므로 발화 사례와 함께 사람이 읽는다.
    """
    guard = candidate.region_restriction_allowed
    for rec in records:
        if guard(rec):
            continue
        candidate.region_restriction_allowed = lambda _rec: True
        try:
            hit = candidate.detect_region_expansion(rec)
        finally:
            candidate.region_restriction_allowed = guard
        if hit:
            yield rec, "v7", hit, "고시금액 이상이라 막음"


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure:
            reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default=str(ROOT / "open/dev.jsonl"))
    parser.add_argument("--labels", default=str(ROOT / "open/dev_labels.csv"),
                        help="있으면 정답을 함께 적는다. 판정에는 쓰지 않는다")
    parser.add_argument("--candidate", default=str(ROOT / "experiments/qualification_candidate.py"))
    parser.add_argument("--items", default="v8,v7,v4")
    parser.add_argument("--output", help="마크다운 검토 시트를 쓸 경로")
    args = parser.parse_args(argv)

    candidate = load_module(Path(args.candidate), "candidate")
    items = [i.strip() for i in args.items.split(",") if i.strip()]
    records = [json.loads(line) for line in
               Path(args.input).read_text(encoding="utf-8").splitlines() if line.strip()]
    labels = read_labels(args.labels)

    lines = ["# 후보 발화 사례 검토 시트", "",
             f"입력 `{Path(args.input).name}` · 공고 {len(records)}건 · 대상 {', '.join(items)}",
             "", "규칙이 근거로 삼은 원문을 그대로 옮겼다. 사람이 읽고 참가자격 제한이 맞는지 표시한다.",
             "정답 열은 대조용이며 판정에 쓰지 않았다.", ""]
    counts = {}
    for rec, item, hit in firings(candidate, records, items):
        gold = labels.get(rec["id"], {}).get(item)
        mark = {"1": "정답 양성", "0": "정답 음성"}.get(gold, "정답 없음")
        counts[(item, mark)] = counts.get((item, mark), 0) + 1
        quote = " ".join(hit["근거문구"].split())
        lines += [f"## {item} · {rec['id']} · {mark}", "",
                  f"- 적용계약법 {rec['meta'].get('적용계약법')} · 업무구분 {rec['meta'].get('업무구분')}"
                  f" · 추정가격 {rec['meta'].get('입찰추정가격')}",
                  f"- 근거문구: {quote}", "- 사람 확인: [ ] 참가자격 제한이 맞다  [ ] 아니다", ""]
    blocked = list(suppressed(candidate, records))
    lines += ["## 가드가 막은 사례", "",
              "규칙 본체는 걸렸는데 가드가 막은 공고다. 가드가 틀리면 여기서 양성을 잃는다.", ""]
    if not blocked:
        lines += ["막은 사례가 없다.", ""]
    for rec, item, hit, reason in blocked:
        gold = labels.get(rec["id"], {}).get(item)
        mark = {"1": "정답 양성", "0": "정답 음성"}.get(gold, "정답 없음")
        quote = " ".join(hit["근거문구"].split())
        lines += [f"### {item} · {rec['id']} · {mark} · {reason}", "",
                  f"- 추정가격 {rec['meta'].get('입찰추정가격')}", f"- 근거문구: {quote}",
                  "- 사람 확인: [ ] 막은 것이 맞다  [ ] 막으면 안 된다", ""]

    lines += ["## 집계", ""]
    for (item, mark), n in sorted(counts.items()):
        lines.append(f"- {item} · {mark}: {n}건")
    lines.append(f"- 가드가 막은 사례: {len(blocked)}건")
    text = "\n".join(lines) + "\n"

    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8", newline="\n")
        print(f"검토 시트 {out}")
    else:
        print(text)
    for (item, mark), n in sorted(counts.items()):
        print(f"{item} {mark} {n}건")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
