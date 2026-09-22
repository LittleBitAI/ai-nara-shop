"""A8 회차의 **인용과 판정을 따로** 감사한다. 모델을 부르지 않고 판정을 바꾸지 않는다.

왜 필요한가. 이웃 wiki 실험이 기각된 방식이 여기서 되풀이될 수 있다 — 모델이 낸 인용이
공고 원문이 아니면 소비자는 **판정을 보류**하고, 그 자리에 baseline 판정이 남는다.
그 baseline 이 우연히 정답이면 지표는 좋아지는데 기전은 하나도 확인되지 않는다.
그래서 이 감사는 셋을 가른다.

1. 모델이 무엇을 냈나 — `software_business`·두 인용 필드의 상태
2. 그 인용이 **공고 원문의 연속 구간인가** — `quote_check`
3. 소비자가 v20 에 무엇을 썼나 — `verify_company_size` 를 **실제로 호출**해서 본다

`gain_kind="fallback_only"` 는 "잘못된 인용 → 판정 보류 → 우연한 baseline 정답" 이다.
**그것만 좋아졌다면 탐색 성공으로 올리지 않는다.** 설계
`artifacts/design/next-step-design-result.md` §4 가 이 계약을 소유한다.

문자열이 검증됐다는 것과 그 조항이 **참여제한 안내인가**는 다른 문제다. 후자는 사람이
`reports/team-c/a8-v20-annex/semantic-review.jsonl` 에 적으며, 그 전까지 `semantic_review`는
`pending` 이고 의미상 적합 인용 수는 null 이다. 여기서 법 해석을 자동으로 만들지 않는다.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import random
import sys
import unicodedata

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import script

# 인용 상태. `invalid` 는 "모델이 냈지만 공고의 연속 구간이 아니다" 다.
QUOTE_STATES = ("null", "empty", "exact", "spacing_restored", "invalid")


def quote_check(quote, rec, visible) -> dict:
    """인용 하나를 공고 원문과 대조한다. 원문을 고치지 않는다.

    `matches` 는 `text[start:end] == effective_quote` 인 자리다 — Python 문자 인덱스이고
    `end` 는 제외다. NFC 재정규화 같은 변형은 하지 않는다. 문서가 `doc_id` 를 안 주면
    `doc_index` 로만 적고 id 를 지어내지 않는다.
    """
    if quote is None:
        return dict(state="null", effective_quote=None, in_visible=False,
                    in_document=False, matches=[])
    if not quote.strip():
        return dict(state="empty", effective_quote=quote, in_visible=False,
                    in_document=False, matches=[])
    restored = script.restore_spacing(quote, rec, visible)
    effective = restored if restored is not None else quote
    matches = []
    for index, doc in enumerate(rec["docs"]):
        text, start = doc["text"], 0
        while True:
            found = text.find(effective, start)
            if found < 0:
                break
            matches.append(dict(doc_id=doc.get("doc_id"), doc_index=index,
                                doc_type=doc.get("type"), start=found,
                                end=found + len(effective)))
            start = found + 1
    in_visible = effective in visible
    if not (in_visible and matches):
        state = "invalid"
    elif restored is not None and restored != quote:
        state = "spacing_restored"
    else:
        state = "exact"
    return dict(state=state, effective_quote=effective, in_visible=in_visible,
                in_document=bool(matches), matches=matches)


def v20_applicable(facts, rec, visible) -> bool:
    """소비자가 v20 을 계산하는 조건. `script.py:739` 의 `applicable` 과 같은 식이다.

    `verify_document_requirements` 의 `quoted()` 가 `restore_spacing` 을 먼저 적용하므로
    여기도 같은 순서로 본다 — `quote_check` 의 `exact`/`spacing_restored` 와 같은 판정이다.
    이 식이 제품과 갈라지면 `tests/test_a8_v20_annex.py` 의 대조 검사가 먼저 깨진다.
    """
    if facts.get("software_business") != "yes":
        return False
    quote = facts.get("software_business_quote")
    effective = script.restore_spacing(quote, rec, visible) or quote
    return bool(effective and effective.strip() and effective in visible
                and any(effective in doc["text"] for doc in rec["docs"]))


def audit_row(rec, facts, *, max_chars) -> dict:
    """공고 하나의 인용 상태와 **실제 소비 결과**를 함께 남긴다."""
    visible = script.build_context(rec, max_chars)
    writes, reason = script.verify_company_size(facts, rec, max_chars)
    cell = writes.get("v20")
    software_docs = [d for d in rec["docs"] if d["type"] in ("공고문", "제안요청서")]
    return dict(
        id=rec["id"], max_chars=max_chars,
        visible_sha256=hashlib.sha256(visible.encode("utf-8")).hexdigest(),
        software_business=facts.get("software_business"),
        software_business_quote_check=quote_check(facts.get("software_business_quote"), rec, visible),
        software_participation_quote_check=quote_check(facts.get("software_participation_quote"),
                                                      rec, visible),
        requirements_complete=facts.get("requirements_complete"),
        input_complete=rec.get("input_completeness", {}).get("완전관측") is True,
        dropped_doc_counts=rec.get("dropped_doc_counts") or {},
        # 관측 보조값이다. 새 게이트가 아니다.
        software_docs_visible=bool(any(d["type"] == "공고문" for d in software_docs)
                                   and all(d["text"].strip() and d["text"] in visible
                                           for d in software_docs)),
        v20_write=None if cell is None else cell["위반여부"],
        v20_action="preserve" if cell is None else f"write_{cell['위반여부']}",
        # 소비자가 v20 을 **계산하기는 했는가.** `software_business != yes` 거나 그 인용이
        # 기각되면 참여 인용이 완벽해도 v20 은 열리지 않는다(script.py:739 의 applicable).
        # 이 값 없이는 "정확한 인용" 과 "쓰인 인용" 이 안 갈린다.
        v20_applicable=v20_applicable(facts, rec, visible),
        company_writes={item: value["위반여부"] for item, value in writes.items()},
        # `outside_general_scope` 여도 v20 은 따로 계산된다. 이것을 v20 차단 이유로 쓰지 않는다.
        company_reason=reason,
        semantic_review="pending")


def _counts(rows) -> dict:
    def state_of(row, field):
        return row[f"{field}_quote_check"]["state"]
    return dict(
        records=len(rows),
        software_yes=sum(1 for r in rows if r["software_business"] == "yes"),
        participation_nonnull=sum(1 for r in rows
                                  if state_of(r, "software_participation") != "null"),
        participation_exact=sum(1 for r in rows
                                if state_of(r, "software_participation") == "exact"),
        participation_spacing_restored=sum(
            1 for r in rows if state_of(r, "software_participation") == "spacing_restored"),
        participation_invalid=sum(1 for r in rows
                                  if state_of(r, "software_participation") == "invalid"),
        v20_write_0=sum(1 for r in rows if r["v20_action"] == "write_0"),
        v20_write_1=sum(1 for r in rows if r["v20_action"] == "write_1"),
        v20_preserve=sum(1 for r in rows if r["v20_action"] == "preserve"),
        # 문자열이 검증된 인용 수와 **의미상 참여제한 안내인** 인용 수는 다르다.
        participation_semantically_applicable=None)


def paired_changes(control_rows, candidate_rows) -> list:
    """두 군에서 v20 또는 인용 상태가 달라진 공고. `fallback_only` 를 따로 표시한다."""
    by_id = {row["id"]: row for row in control_rows}
    out = []
    for after in candidate_rows:
        before = by_id[after["id"]]
        fields = {}
        for field in ("v20_action", "software_business"):
            if before[field] != after[field]:
                fields[field] = [before[field], after[field]]
        for field in ("software_business", "software_participation"):
            key = f"{field}_quote_check"
            if before[key]["state"] != after[key]["state"]:
                fields[f"{field}_quote_state"] = [before[key]["state"], after[key]["state"]]
        if not fields:
            continue
        out.append(dict(id=after["id"], fields=fields, gain_kind=gain_kind(before, after),
                        semantic_review="pending"))
    return out


def gain_kind(before, after) -> str:
    """기전을 **실제 v20 전이**로 판정한다. 인용 상태만으로 부르지 않는다.

    왜 인용만으로는 안 되나. 두 가지가 조용히 섞인다.

    - `software_business != yes` 인 공고는 v20 이 애초에 안 열린다. 참여 인용이
      정확해도 **그 인용은 아무것도 세우지 않았다.** 그것을 `verified_quote` 로
      세면 닿지도 않은 경로가 기전으로 집계된다.
    - 양쪽 다 `preserve` 인데 인용 상태만 `null → invalid` 로 바뀐 것은
      판정이 하나도 안 움직인 것이다. 그것을 `fallback_only` 로 세면
      "우연한 baseline 이득" 이 실제보다 많아 보인다.

    그래서 둘로 좁힌다.

    - `verified_quote` — 후보에서 v20 이 **적용 가능**하고 참여 인용이 검증됐으며
      판정이 실제로 `write_0` 으로 **전이**했다.
    - `verified_absence` — 적용 가능하고 참여 인용이 **없어서**(`null`) 소비자가
      부재 위반을 새로 썼다(`write_1` 으로 전이). **v20 은 부재탐지 항목이라
      이쪽이 주 기전이다** — H4 의 v20 양성 5건이 전부 이 분기였다.
      이것을 `other` 로 두면 "먼저 볼 숫자" 가 기전을 놓친다(라운드 2 P1).
    - `fallback_only` — 대조군에서 v20 이 쓰였는데(`write_*`) 후보에서 **두 필수 인용 중
      어느 쪽이든** 기각돼(`invalid`/`empty`) 또는 적용성이 무너져 **`preserve` 로 내려앉았다.**
      지표가 좋아졌다면 그 자리를 채운 것은 baseline 이지 이 주입이 아니다.
    - 나머지는 `other` 다. 이름을 붙이지 않는 것이 잘못 붙이는 것보다 낫다.
    """
    def state_of(row, field):
        return row[f"{field}_quote_check"]["state"]

    if before["v20_action"] == after["v20_action"]:
        return "other"                       # 판정이 안 움직였으면 이득도 손실도 아니다
    verified = state_of(after, "software_participation") in ("exact", "spacing_restored")
    if after["v20_applicable"] and after["v20_action"] == "write_0" and verified:
        return "verified_quote"
    if (after["v20_applicable"] and after["v20_action"] == "write_1"
            and state_of(after, "software_participation") == "null"):
        return "verified_absence"
    if before["v20_action"].startswith("write_") and after["v20_action"] == "preserve":
        # 적용성을 세우는 business 인용이든 참여 인용이든, 기각이 보류를 만들었으면 같은 실패다.
        rejected = any(state_of(after, field) in ("invalid", "empty")
                       for field in ("software_business", "software_participation"))
        if rejected or not after["v20_applicable"]:
            return "fallback_only"
    return "other"


def audit_episode(episode_dir, *, dev_path=None, data_dir=None) -> dict:
    """회차 폴더의 군별 원응답을 읽어 감사한다. 판정 코드는 그대로 쓴다."""
    episode_dir = Path(episode_dir)
    dev_path = Path(dev_path or ROOT/"open/dev.jsonl")
    data_dir = str(data_dir or ROOT/"open/data")
    # 카탈로그 전역을 **제품이 채우는 것과 같은 방식으로** 채운다. 안 채우면
    # `competitive_product()` 가 None 이라 v12·v13 경로가 닫히고 감사가 0 을 돌려준다.
    script.load_sme_reference(data_dir)
    if not script._PRODUCTS:
        raise ValueError("카탈로그 전역이 비었다. 이 상태의 0 은 안전의 증거가 아니다")
    contract = json.loads((episode_dir/"contract.json").read_text(encoding="utf-8"))
    records = {rec["id"]: rec for rec in script.iter_records(str(dev_path))}
    if sorted(records) != sorted(contract["dev_ids"]):
        raise ValueError("회차 계약의 공고 집합이 입력과 다르다")
    arms = {}
    for name in contract["arms"]:
        payload = json.loads((episode_dir/name/"dev.json").read_text(encoding="utf-8"))
        if payload["contract_sha256"] != _digest(contract):
            raise ValueError(f"{name}: 계약 hash 가 다르다")
        # 계약 hash 와 id 집합만 보면 **원응답을 바꿔도 감사가 통과한다.** 파일이 스스로
        # 적어 둔 payload hash 를 다시 계산해 그 경로를 막는다.
        if payload["payload_sha256"] != _digest(payload["payload"]):
            raise ValueError(f"{name}: 저장 원응답 hash 가 다르다 — 산출물이 바뀌었다")
        rows = []
        seen = set()
        for row in payload["payload"]["rows"]:
            if row["id"] in seen:
                raise ValueError(f"{name}: 공고가 중복됐다 {row['id']}")
            seen.add(row["id"])
            facts = script.parse_judgment(
                row["response_text"], expected_items=script.COMPANY_SIZE_KEYS)[0]["company_size"]
            rows.append(audit_row(records[row["id"]], facts, max_chars=row["max_chars"]))
        if sorted(seen) != sorted(contract["dev_ids"]):
            raise ValueError(f"{name}: 응답 공고 집합이 계약과 다르다")
        arms[name] = dict(rows=rows, counts=_counts(rows))
    order = contract["order"]
    control, candidate = order[0], order[-1]
    if control == candidate:
        raise ValueError("두 군이 필요하다")
    pairs = paired_changes(arms["control"]["rows"], arms[[n for n in arms if n != "control"][0]]["rows"])
    return dict(source_commit=contract["source_commit"], contract_sha256=_digest(contract),
                execution_mode="cpu_audit", episode=contract["episode"], order=order,
                arms=arms, paired_changes=pairs,
                complete=all(arm["counts"]["records"] == len(contract["dev_ids"])
                             for arm in arms.values()),
                semantic_review_complete=False)


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def select_sample(dev_ids, software_yes_ids, positive_ids, *, random_n=30, seed=20260922) -> dict:
    """API 표본. 필수 층은 **적용 대상 합집합 + 라벨 양성**이고 나머지는 무작위다.

    필수 층을 한 회차로 고정하지 않는 이유는 실측이다 — `software_business=yes` 집합이
    회차마다 흔들린다(H4 11 · wiki 회차1 11 · wiki 회차2 12, 교집합 9, 합집합 14).
    한 회차로 고정하면 그 회차의 답에 표본이 편향되고, 교집합으로 좁히면 어떤 회차에서
    적용 대상이 되는 공고를 표본에서 빼게 된다. 근거는
    `artifacts/design/verification-before-implementation.md` §3.
    """
    dev = list(dict.fromkeys(dev_ids))
    mandatory = set(software_yes_ids) | set(positive_ids)
    unknown = mandatory - set(dev)
    if unknown:
        raise ValueError("입력 밖의 공고가 필수 층에 있다: " + ", ".join(sorted(unknown)))
    pool = sorted(set(dev) - mandatory)
    if len(pool) < random_n:
        raise ValueError(f"무작위 표본이 부족하다: {len(pool)} < {random_n}")
    drawn = set(random.Random(seed).sample(pool, random_n))
    selected = [i for i in dev if i in mandatory or i in drawn]   # 실행 순서는 원래 dev 순서
    strata = {}
    for identifier in selected:
        tags = []
        if identifier in set(software_yes_ids):
            tags.append("software_yes")
        if identifier in set(positive_ids):
            tags.append("label_positive")
        if identifier in drawn:
            tags.append("random")
        strata[identifier] = tags
    return dict(seed=seed, random_n=random_n, mandatory_ids=sorted(mandatory),
                random_ids=sorted(drawn), selected_ids=selected, strata_by_id=strata,
                note="라벨은 표본 선정과 사후 채점에만 쓴다. 모델 메시지에 넣지 않는다")


def _yes_from(path) -> tuple:
    """한 회차의 저장 company 응답에서 `software_business=yes` 집합과 그 원천 hash."""
    path = Path(path)
    if path.is_dir():
        # 전체 파이프라인 회차 폴더(`.../dev-debug`)다. 진단에서 원응답을 읽는다.
        from tools import replay_run
        texts = replay_run.saved_responses(path)["company_size"]
        rows = [dict(id=identifier, response_text=text) for identifier, text in texts.items()]
        source = path/"diagnostics.jsonl"
    else:
        value = json.loads(path.read_text(encoding="utf-8"))
        rows = value["payload"]["rows"] if "payload" in value else value["rows"]
        source = path
    found = {row["id"] for row in rows
             if script.parse_judgment(row["response_text"],
                                      expected_items=script.COMPANY_SIZE_KEYS
                                      )[0]["company_size"]["software_business"] == "yes"}
    return found, dict(count=len(found), ids=sorted(found), source=source.as_posix(),
                       sha256=hashlib.sha256(source.read_bytes()).hexdigest())


def software_yes_ids(*payload_paths) -> dict:
    """여러 회차의 저장 응답에서 `software_business=yes` 집합을 모은다.

    합집합을 쓴다 — 이 집합은 회차 산출물이라 회차마다 흔들린다(실측: 11 · 11 · 12, 교집합 9).
    """
    per_run, union, common = {}, set(), None
    for path in payload_paths:
        found, record = _yes_from(path)
        per_run[record["source"]] = record
        union |= found
        common = found if common is None else (common & found)
    return dict(per_run=per_run, union=sorted(union), union_count=len(union),
                intersection=sorted(common or ()), intersection_count=len(common or ()))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--episode-dir", type=Path, help="회차 폴더. 감사 결과를 그 안에 쓴다")
    parser.add_argument("--sample-out", type=Path, help="표본 manifest 를 쓸 경로")
    parser.add_argument("--yes-source", type=Path, nargs="*", default=(),
                        help="`software_business=yes` 를 모을 회차 payload 들")
    parser.add_argument("--labels", type=Path, default=ROOT/"open/dev_labels.csv")
    parser.add_argument("--dev-input", type=Path, default=ROOT/"open/dev.jsonl")
    parser.add_argument("--random-n", type=int, default=30)
    parser.add_argument("--seed", type=int, default=20260922)
    args = parser.parse_args(argv)
    if args.episode_dir:
        result = audit_episode(args.episode_dir, dev_path=args.dev_input)
        out = args.episode_dir/"v20-audit.json"
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                       encoding="utf-8", newline="\n")
        print(json.dumps({name: arm["counts"] for name, arm in result["arms"].items()},
                         ensure_ascii=False, indent=2))
        print(f"바뀐 공고 {len(result['paired_changes'])}건 → {out}")
    if args.sample_out:
        import csv
        with args.labels.open(encoding="utf-8-sig", newline="") as source:
            positives = {row["id"] for row in csv.DictReader(source) if row["v20"] == "1"}
        collected = software_yes_ids(*args.yes_source)
        dev_ids = [rec["id"] for rec in script.iter_records(str(args.dev_input))]
        sample = select_sample(dev_ids, collected["union"], positives,
                              random_n=args.random_n, seed=args.seed)
        sample["sources"] = collected
        sample["dev_input_sha256"] = hashlib.sha256(args.dev_input.read_bytes()).hexdigest()
        sample["labels_sha256"] = hashlib.sha256(args.labels.read_bytes()).hexdigest()
        sample["python"] = sys.version.split()[0]
        sample["algorithm"] = "random.Random(seed).sample(sorted(dev - mandatory), random_n)"
        args.sample_out.parent.mkdir(parents=True, exist_ok=True)
        args.sample_out.write_text(json.dumps(sample, ensure_ascii=False, indent=2) + "\n",
                                   encoding="utf-8", newline="\n")
        print(f"표본 {len(sample['selected_ids'])}건(필수 {len(sample['mandatory_ids'])}"
              f" + 무작위 {args.random_n}) → {args.sample_out}")
    if not (args.episode_dir or args.sample_out):
        parser.error("--episode-dir 또는 --sample-out 이 필요하다")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
