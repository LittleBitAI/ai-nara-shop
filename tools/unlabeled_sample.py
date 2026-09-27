"""무라벨 감사 표본의 공고 ID 순서를 고정한다. 모델을 부르지 않는다.

[설계](../artifacts/review/unlabeled-design-result.md) 2절: 이미 열어 본 공고를 빼고, 라벨과 무관한
고정 난수 순서(seed 20260923)로 전체 ID 에서 추첨한다. 파일 앞 N행을 고르는 `--limit` 은
무작위 표집이 아니다. 처음 2,000건을 돌리고 삭제 집합이 모자라면 **같은 순서로** 6,000건까지
늘리므로, 순서 전체의 앞 6,000개를 파일로 남긴다.

제외 규칙은 둘이다.
- 이미 라벨을 열어 본 공고 ID(`--seen`, JSONL 의 `id`)
- 그 공고와 문서 본문이 바이트 단위로 같은 공고. 같은 문서를 다른 ID 로 다시 보는 것은 새 관측이 아니다

유사 템플릿은 지우지 않는다 — 모집단을 자의로 바꾸는 일이다.
"""

import argparse
import hashlib
import json
import random
import sys
from pathlib import Path

SEED = 20260923
KEEP = 6000


def body_hash(record):
    docs = [(d.get("type"), d.get("text")) for d in record.get("docs") or []]
    return hashlib.sha256(json.dumps(docs, ensure_ascii=False).encode("utf-8")).hexdigest()


def draw(records, seen_ids, *, seed=SEED, keep=KEEP):
    """(추첨 순서 ID 목록, 제외 기록). records 는 {'id', 'docs'} 의 반복자다."""
    by_id, hashes = {}, {}
    for record in records:
        identifier = record["id"]
        if identifier in by_id:
            raise ValueError(f"입력에 중복 ID 가 있다: {identifier}")
        by_id[identifier] = body_hash(record)
        hashes.setdefault(by_id[identifier], []).append(identifier)
    missing = sorted(set(seen_ids) - set(by_id))
    if missing:
        raise ValueError(f"본 적 있는 ID 가 입력에 없다: {missing[:5]}")
    seen_hashes = {by_id[i] for i in seen_ids}
    excluded = {i: ("seen" if i in seen_ids else "duplicate_of_seen")
                for h in seen_hashes for i in hashes[h]}
    population = sorted(i for i in by_id if i not in excluded)
    random.Random(seed).shuffle(population)
    return population[:keep], {"population": len(population), "excluded": excluded}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--input", required=True, help="open/train_unlabeled.jsonl")
    parser.add_argument("--seen", required=True, help="이미 라벨을 본 공고의 JSONL (id 키)")
    parser.add_argument("--out", required=True, help="추첨 순서 ID 를 한 줄에 하나씩 쓴다")
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--keep", type=int, default=KEEP, help="순서 앞에서 남길 ID 수")
    args = parser.parse_args(argv)
    seen = {json.loads(line)["id"] for line in Path(args.seen).read_text(encoding="utf-8").splitlines()
            if line.strip()}
    raw = Path(args.input).read_bytes()
    # splitlines() 는 본문 안의 U+2028 같은 구분자에서도 끊는다. JSONL 의 행 경계는 줄바꿈뿐이다.
    records = (json.loads(line) for line in raw.decode("utf-8").split("\n") if line.strip())
    order, info = draw(records, seen, seed=args.seed, keep=args.keep)
    out = Path(args.out)
    if out.exists():
        print(f"error: {out} 가 이미 있다", file=sys.stderr)
        return 1
    out.write_text("\n".join(order) + "\n", encoding="utf-8", newline="\n")
    manifest = {"seed": args.seed, "kept": len(order), "population": info["population"],
                "excluded": info["excluded"], "seen_source": Path(args.seen).as_posix(),
                "input_sha256": hashlib.sha256(raw).hexdigest(),
                "ids_sha256": hashlib.sha256(out.read_bytes()).hexdigest()}
    out.with_suffix(".manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({k: v for k, v in manifest.items() if k != "excluded"}, ensure_ascii=False))
    print(f"제외 {len(info['excluded'])}건 (본 공고 {sum(v == 'seen' for v in info['excluded'].values())})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
