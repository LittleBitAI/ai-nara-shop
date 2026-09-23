"""모델 없이 검증하는 제출 계약·실패 회귀 검사. live 성능 검사가 아니다."""

import copy
import csv
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("baseline", ROOT / "script.py")
baseline = importlib.util.module_from_spec(spec)
spec.loader.exec_module(baseline)


def record():
    return {"id": "sample", "docs": [{"doc_id": "a", "type": "공고문", "text": "공고 본문입니다."}],
            "meta": {"적용계약법": "국가", "지역제한여부": None},
            "input_completeness": {"완전관측": False}, "dropped_doc_counts": {"규격서": 1}}


def valid():
    return {v: {"위반여부": 0, "근거문구": None} for v in baseline.ITEMS}


class BaselineTests(unittest.TestCase):
    def test_selective_v13_preserves_sparse_rows_and_skips_empty_selection(self):
        for positives in (set(), {1, 3}):
            calls = []
            class Selective(baseline.MockRunner):
                def chat(self, batch, items=None):
                    calls.append((items, len(batch)))
                    if items == baseline.SME_ITEMS:
                        return [json.dumps({"v13": {"facts": baseline.empty_sme_facts(),
                                                   "위반여부": 0, "근거문구": None}})] * len(batch)
                    if items == baseline.COMPANY_SIZE_KEYS:
                        return super().chat(batch, items)
                    if items is not None:   # 추가 호출은 facts 없이 두 칸만 낸다
                        return [json.dumps({k: {"위반여부": 0, "근거문구": None}
                                            for k in items})] * len(batch)
                    outputs = []
                    for i in range(len(batch)):
                        obj = valid()
                        obj["v13"]["위반여부"] = int(i in positives)
                        obj["v10"]["위반여부"] = 1
                        outputs.append(json.dumps(obj))
                    return outputs
            with tempfile.TemporaryDirectory() as tmp:
                out = Path(tmp) / "submission.csv"
                report = baseline.run(str(ROOT / "open/data/test.jsonl.gz"), str(out), Selective,
                                      limit=4, chunk=128, max_chars=16000, data_dir=str(ROOT / "open/data"))
                # 합동 1회 → v13 추가 호출(선택 공고가 있을 때만) → 켜져 있는 추가 호출.
                # 순서는 run()이 부르는 순서 그대로다: split → company_size → product.
                # 시험 입력 4건은 전부 고시금액 미만이라 분할 호출이 4건 모두에 붙는다.
                expected = [(None, 4)] + [(["v13"], 2)] * bool(positives)
                if baseline.SPLIT_ITEMS:
                    expected.append((baseline.SPLIT_ITEMS, 4))
                if baseline.BAND_ITEMS:
                    expected.append((baseline.COMPANY_SIZE_KEYS, 4))
                if baseline.PRODUCT_ITEMS:
                    expected.append((baseline.PRODUCT_ITEMS, 4))
                self.assertEqual(calls, expected)
                self.assertEqual(report["sme_selected_count"], len(positives))
                self.assertEqual(report["sme_skipped_count"], 4 - len(positives))
                self.assertEqual(report["sme_fallback_count"], 0)
                with out.open(encoding="utf-8") as stream:
                    final = list(csv.DictReader(stream))
                with out.with_name("baseline_submission.csv").open(encoding="utf-8") as stream:
                    original = list(csv.DictReader(stream))
                # 추가 호출이 건드릴 수 있는 칸은 v13과 N3 경쟁제품 3항목뿐이다.
                # 그 밖이 하나라도 움직이면 colab-1789719173182820657의 실패가 되풀이된 것이다.
                touched = {"v13", "e13"} | {c for v in baseline.PRODUCT_ITEMS
                                            for c in (v, "e" + v[1:])}
                for i, (before, after) in enumerate(zip(original, final)):
                    self.assertEqual(after["v13"], "0")
                    for col in baseline.COLUMNS:
                        if col in touched:
                            continue
                        self.assertEqual(before[col], after[col])
                events = [json.loads(line) for line in out.with_name("diagnostics.jsonl").read_text(
                    encoding="utf-8").splitlines()]
                responses = [e for e in events if e["event"] == "response" and e["phase"] == "sme"]
                self.assertEqual([e["global_index"] for e in responses], sorted(positives))
                self.assertEqual([e["id"] for e in responses], [original[i]["id"] for i in sorted(positives)])

    def test_sme_facts_require_real_scope_and_qualification(self):
        rec = record()
        rec["input_completeness"] = {"완전관측": True}
        rec["dropped_doc_counts"] = {}
        rec["docs"][0]["text"] = "활성탄 1110152201 구매. 「중소기업기본법」에 따른 소기업·소상공인 확인서를 소지한 업체."
        _, products = baseline.load_sme_reference(str(ROOT / "open/data"))
        facts = dict(product_code="1110152201", scope_quote="활성탄 1110152201 구매.", scope_matches="yes",
                     qualification_quote=None, qualification="missing", exception_applies="no")
        obj = {k: {"facts": dict(facts), "위반여부": 1, "근거문구": None} for k in baseline.SME_ITEMS}
        obj["v13"]["facts"].update(qualification="small_only",
                                  qualification_quote="「중소기업기본법」에 따른 소기업·소상공인 확인서를 소지한 업체.")
        parsed, _ = baseline.parse_judgment(json.dumps(obj), baseline.SME_ITEMS, sme=True)
        result, _ = baseline.verify_sme(parsed, rec, products, 16000)
        self.assertEqual([result[k]["위반여부"] for k in baseline.SME_ITEMS], [1])
        self.assertEqual(result["v13"]["근거문구"], obj["v13"]["facts"]["qualification_quote"])
        for field, value in [("product_code", "9999999999"), ("scope_quote", "원문에 없는 문구"),
                             ("scope_matches", "unknown"), ("exception_applies", "yes")]:
            bad = copy.deepcopy(parsed)
            for cell in bad.values():
                cell["facts"][field] = value
            result, _ = baseline.verify_sme(bad, rec, products, 16000)
            self.assertTrue(all(cell["위반여부"] == 0 for cell in result.values()))
        rec["docs"][0]["text"] += " 중 · 소기업·소상공인 확인서를 소지한 업체."
        parsed["v13"]["facts"]["qualification_quote"] = "중 · 소기업·소상공인 확인서를 소지한 업체."
        result, reasons = baseline.verify_sme(parsed, rec, products, 16000)
        self.assertEqual(result["v13"]["위반여부"], 0)
        self.assertIn("clause_includes_medium_enterprises", reasons["v13"])
        rec["docs"][0]["text"] += " 「중소기업확인서」를 소지한 업체."
        parsed["v13"]["facts"]["qualification_quote"] = "「중소기업확인서」를 소지한 업체."
        result, _ = baseline.verify_sme(parsed, rec, products, 16000)
        self.assertEqual(result["v13"]["위반여부"], 0)
        for bad_value in [True, "maybe", None]:
            bad = copy.deepcopy(obj)
            bad["v13"]["facts"]["scope_matches"] = bad_value
            with self.assertRaises(ValueError):
                baseline.parse_judgment(json.dumps(bad), baseline.SME_ITEMS, sme=True)
        del obj["v13"]["facts"]
        with self.assertRaises(ValueError):
            baseline.parse_judgment(json.dumps(obj), baseline.SME_ITEMS, sme=True)

    def test_english_instructions_preserve_korean_source_and_fact_schema(self):
        laws, products = baseline.load_sme_reference(str(ROOT / "open/data"))
        table = baseline.item_table(str(ROOT / "open/data"))
        system = baseline.build_system_prompt(table)
        focused = baseline.build_system_prompt(table, laws, baseline.SME_ITEMS)
        self.assertTrue(system.startswith("Audit this Korean"))
        self.assertIn("extract facts BEFORE deciding", focused)
        self.assertIn(laws, focused)
        for item in baseline.ITEMS:
            self.assertIn(table[item]["항목명"], system)
        rec = record()
        self.assertIn(rec["docs"][0]["text"], baseline.build_user_prompt(rec, 16000, products))
        runner = object.__new__(baseline.VLLMRunner)
        runner.sp = SimpleNamespace(structured_outputs=SimpleNamespace(
            json=baseline.decode_schema(str(ROOT / "open/data"))))
        schema = runner.parameters_for_items(baseline.SME_ITEMS).structured_outputs.json
        self.assertEqual(set(schema["properties"]), set(baseline.SME_ITEMS))
        self.assertIn("facts", schema["properties"]["v13"]["required"])
        self.assertEqual(schema["properties"]["v13"]["properties"]["근거문구"], {"type": "null"})
        output = {k: {"facts": baseline.empty_sme_facts(), "위반여부": 0, "근거문구": None}
                  for k in baseline.SME_ITEMS}
        self.assertEqual(baseline.parse_judgment(json.dumps(output), baseline.SME_ITEMS, sme=True)[0], output)
        self.assertNotIn("facts", runner.sp.structured_outputs.json["properties"]["v13"]["properties"])

    def test_isolated_sme_preserves_other_items_and_publishes_paired_results(self):
        calls, instances = [], []
        expected_system = baseline.build_system_prompt(baseline.item_table(str(ROOT / "open/data")))
        class Isolated(baseline.MockRunner):
            def __init__(self, schema, **kwargs):
                instances.append(self)
            def chat(self, batch, items=None):
                calls.append(items)
                if items == baseline.COMPANY_SIZE_KEYS:
                    return super().chat(batch, items)
                outputs = []
                for messages in batch:
                    if items is None:
                        self_test.assertEqual(messages[0]["content"], expected_system)
                        self_test.assertNotIn("[Provided 고시", messages[1]["content"])
                    elif items == baseline.SPLIT_ITEMS:
                        # N1 분할 호출: 합동 프롬프트와 다른 항목 목록, 고시 자료는 안 붙는다.
                        self_test.assertNotIn("- v24:", messages[0]["content"])
                        self_test.assertNotIn("[Provided 고시", messages[1]["content"])
                    else:
                        self_test.assertEqual(items, ["v13"])
                        self_test.assertNotIn("- v24:", messages[0]["content"])
                        self_test.assertIn("[Provided 고시", messages[1]["content"])
                    # 두 시험 공고의 본문에 공통으로 있는 구절이다. 근거 계약이 검증된
                    # 인용을 요구하므로 여기서 빈칸을 내면 baseline 의 v13 양성이 서지 않아
                    # SME 가 그것을 내렸다는 것을 볼 수 없다.
                    obj = {k: {"위반여부": 1, "근거문구": "국가종합전자조달시스템"}
                           for k in (items or baseline.ITEMS)}
                    if items == baseline.SME_ITEMS:
                        obj["v13"]["위반여부"] = 0
                        for cell in obj.values():
                            cell["facts"] = baseline.empty_sme_facts()
                    outputs.append(json.dumps(obj))
                return outputs
        self_test = self
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "submission.csv"
            report = baseline.run(str(ROOT / "open/data/test.jsonl.gz"), str(out), Isolated,
                                  limit=2, chunk=128, max_chars=16000, data_dir=str(ROOT / "open/data"))
            self.assertEqual(len(instances), 1)
            expected = [None, ["v13"]]
            if baseline.SPLIT_ITEMS:
                expected.append(baseline.SPLIT_ITEMS)
            if baseline.BAND_ITEMS:
                expected.append(baseline.COMPANY_SIZE_KEYS)
            if baseline.PRODUCT_ITEMS:
                expected.append(baseline.PRODUCT_ITEMS)
            # 켜진 추가 호출 말고 다른 항목 목록이 오면 실패한다.
            self.assertEqual(calls, expected)
            with out.open(encoding="utf-8") as f:
                final = list(csv.DictReader(f))
            with out.with_name("baseline_submission.csv").open(encoding="utf-8") as f:
                original = list(csv.DictReader(f))
            for before, after in zip(original, final):
                self.assertEqual(before["v13"], "1")
                self.assertEqual(after["v13"], "0")
                # 추가 호출이 건드릴 수 있는 칸은 v13과 N1 분할 2항목뿐이다.
                # 그 밖의 항목이 하나라도 움직이면 회차 colab-1789719173182820657의
                # 실패(대상 밖 여덟 항목이 TP 열하나를 잃음)가 되풀이된 것이다.
                touched = ["v13", "e13"]
                for item in baseline.SPLIT_ITEMS:
                    touched += [item, "e" + item[1:]]
                for col in baseline.COLUMNS:
                    if col not in touched:
                        self.assertEqual(before[col], after[col])
            self.assertIn("sme_inference_seconds", report)
            self.assertEqual(report["sme_model_success_count"], 0)  # Test double is not live evidence.
        class BrokenSubset(Isolated):
            def chat(self, batch, items=None):
                return ["{}"] * len(batch) if items is not None else super().chat(batch)
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "submission.csv"
            report = baseline.run(str(ROOT / "open/data/test.jsonl.gz"), str(out), BrokenSubset,
                                  limit=1, chunk=128, max_chars=16000, data_dir=str(ROOT / "open/data"))
            self.assertEqual(out.read_bytes(), out.with_name("baseline_submission.csv").read_bytes())
            self.assertEqual(report["sme_fallback_count"], 1)
            self.assertEqual(report["sme_verified_count"], 0)
            self.assertEqual(report["sme_model_success_count"], 0)
            events = [json.loads(line) for line in out.with_name("diagnostics.jsonl").read_text(
                encoding="utf-8").splitlines()]
            fallback = next(e for e in events if e["event"] == "sme_fallback")
            self.assertIn("정상 1항목", fallback["error_message"])
            self.assertEqual(fallback["id"], "PPS-S-0001")

    def test_split_retry_validates_every_group_without_changing_defaults(self):
        runner = object.__new__(baseline.VLLMRunner)
        runner.sp = SimpleNamespace(max_tokens=2048, structured_outputs=SimpleNamespace(
            json=baseline.decode_schema(str(ROOT / "open/data"))))
        runner.count_tokens = lambda messages: 14000
        good = valid()
        good["v10"]["위반여부"] = 1
        calls = []
        def chat(batch, sampling_params, **kwargs):
            keys = sampling_params.structured_outputs.json["required"]
            if len(keys) in (1, 6):
                for k in keys:
                    if k not in baseline.ABSENCE and "facts" not in sampling_params.structured_outputs.json["properties"][k]["properties"]:
                        self.assertEqual(sampling_params.structured_outputs.json["properties"][k]
                                         ["properties"]["근거문구"]["maxLength"], 100)
            calls.append(list(keys))
            # A deterministic all-item completion always truncates; smaller schemas succeed.
            cells = {k: dict(good[k]) for k in keys}
            if "facts" in sampling_params.structured_outputs.json["properties"][keys[0]]["properties"]:
                for cell in cells.values():
                    cell["facts"] = baseline.empty_sme_facts()
            text = json.dumps(cells) if len(keys) <= 6 else '{"v1":'
            return [SimpleNamespace(outputs=[SimpleNamespace(text=text, token_ids=[1],
                    finish_reason="stop" if len(keys) <= 6 else "length", stop_reason=None)],
                    prompt_token_ids=[1])]
        runner.llm = SimpleNamespace(chat=chat)
        messages = [{"role": "system", "content": "판정 지시"}, {"role": "user", "content": "공고 원문"}]
        original = copy.deepcopy(messages)
        result = baseline.run_chunk(runner, [messages])
        self.assertEqual(baseline.parse_judgment(result[0])[0], good)
        self.assertEqual([len(keys) for keys in calls], [24, 6, 6, 6, 6])
        self.assertEqual(sum(calls[1:], []), baseline.ITEMS)
        self.assertEqual(messages, original)
        self.assertEqual(runner.sp.max_tokens, 2048)
        self.assertEqual(runner.sp.structured_outputs.json["required"], baseline.ITEMS)
        self.assertEqual(runner.sp.structured_outputs.json["properties"]["v1"]
                         ["properties"]["근거문구"]["maxLength"], 500)
        runner.llm.chat = lambda *a, **kw: [SimpleNamespace(outputs=[], prompt_token_ids=[1])]
        with self.assertRaises(RuntimeError):
            baseline.run_chunk(runner, [messages])
        def bad_second_group(batch, sampling_params, **kwargs):
            outputs = chat(batch, sampling_params, **kwargs)
            if sampling_params.structured_outputs.json["required"] == baseline.ITEMS[6:12]:
                outputs[0].outputs[0].text = "{}"
            return outputs
        runner.llm.chat = bad_second_group
        calls.clear()
        result = baseline.run_chunk(runner, [messages])
        self.assertEqual(baseline.parse_judgment(result[0])[0], good)
        self.assertEqual([len(keys) for keys in calls], [24, 6, 6, 1, 1, 1, 1, 1, 1, 6, 6])
        self.assertEqual(calls[3:9], [[k] for k in baseline.ITEMS[6:12]])
        runner.count_tokens = lambda messages: baseline.MAX_MODEL_LEN - 64
        with self.assertRaisesRegex(RuntimeError, "토큰 예산 없음"):
            baseline.run_chunk(runner, [messages])
        runner.count_tokens = lambda messages: 14000
        def broken_first(batch, sampling_params, **kwargs):
            outputs = chat(batch, sampling_params, **kwargs)
            if len(calls) == 1:
                outputs[0].outputs[0].text = "{}"
            return outputs
        runner.llm.chat = broken_first
        calls.clear()
        result = baseline.run_chunk(runner, [messages], items=baseline.SME_ITEMS, phase="sme")
        self.assertEqual([len(keys) for keys in calls], [1, 1])
        self.assertEqual(baseline.parse_judgment(result[0], expected_items=baseline.SME_ITEMS, sme=True)[0],
                         {k: {**good[k], "facts": baseline.empty_sme_facts()} for k in baseline.SME_ITEMS})

    def test_equivalent_responses_do_not_retry_chunk_62(self):
        for items in (None, baseline.SME_ITEMS):
            keys = items or baseline.ITEMS
            canonical = {k: {"위반여부": 0, "근거문구": None} for k in keys}
            if items:
                for cell in canonical.values():
                    cell["facts"] = baseline.empty_sme_facts()
            for value, expected in [(True, 1), (False, 0), (1.0, 1), (0.0, 0),
                                    (" 1 ", 1), ("0", 0), ("true", 1), ("FALSE", 0)]:
                obj = copy.deepcopy(canonical)
                obj[keys[0]].update(위반여부=value, explanation="ignored")
                obj["comment"] = "ignored"
                if items:
                    obj[keys[0]]["facts"]["comment"] = "ignored"
                good, variant = json.dumps(canonical), json.dumps(obj)
                calls = []
                class Runner:
                    def chat(self, batch, **kwargs):
                        calls.append(len(batch))
                        return [good] * 62 + [variant] + [good] * 65
                    def retry_chat(self, *args, **kwargs):
                        raise AssertionError("equivalent response must not be retried")
                with self.subTest(items=items, value=value):
                    outputs = baseline.run_chunk(Runner(), [[] for _ in range(128)],
                                                 items=items, phase="sme" if items else "baseline")
                    self.assertEqual(calls, [128])
                    parsed, missing = baseline.parse_judgment(outputs[62], keys, sme=bool(items))
                    expected_cells = copy.deepcopy(canonical)
                    expected_cells[keys[0]]["위반여부"] = expected
                    self.assertEqual(parsed, expected_cells)
                    self.assertIs(type(parsed[keys[0]]["위반여부"]), int)
                    self.assertEqual(missing, [])

    def test_chunk_62_fallback_requires_valid_baseline_and_preserves_neighbors(self):
        good = json.dumps(valid())
        focused = json.dumps({k: {"facts": baseline.empty_sme_facts(), "위반여부": 1,
                                  "근거문구": None} for k in baseline.SME_ITEMS})
        class Broken:
            def chat(self, batch, items=None):
                return [focused] * 62 + ["{}"] + [focused] * 65
            def retry_chat(self, batch, items=None):
                raise ValueError("injected retry failure")
        events = []
        kwargs = dict(start=128, ids=[f"notice-{i}" for i in range(128)], items=baseline.SME_ITEMS,
                      phase="sme", emit=lambda event, **fields: events.append({"event": event, **fields}))
        batch = [[] for _ in range(128)]
        result = baseline.run_chunk(Broken(), batch, baseline_texts=[good] * 128, **kwargs)
        self.assertIsNone(result[62])
        self.assertTrue(all(text == focused for i, text in enumerate(result) if i != 62))
        fallback = next(e for e in events if e["event"] == "sme_fallback")
        self.assertEqual((fallback["chunk_index"], fallback["global_index"], fallback["id"]),
                         (62, 190, "notice-62"))
        with self.assertRaisesRegex(RuntimeError, "global_index=190"):
            baseline.run_chunk(Broken(), batch, **kwargs)
        invalid = [good] * 128
        invalid[62] = "{}"
        with self.assertRaises(ValueError):
            baseline.run_chunk(Broken(), batch, baseline_texts=invalid, **kwargs)
        with self.assertRaises(ValueError):
            baseline.run_chunk(Broken(), batch, baseline_texts=[good] * 127, **kwargs)
        with self.assertRaises(ValueError):
            baseline.run_chunk(Broken(), batch, baseline_texts=[good] * 128)
        events.clear()
        indices = list(range(128, 384, 2))
        baseline.run_chunk(Broken(), batch, baseline_texts=[good] * 128, indices=indices, **kwargs)
        fallback = next(e for e in events if e["event"] == "sme_fallback")
        self.assertEqual(fallback["global_index"], indices[62])
        with self.assertRaisesRegex(ValueError, "인덱스 건수"):
            baseline.run_chunk(Broken(), batch, indices=indices[:-1], **kwargs)

    def test_provided_law_and_product_context(self):
        laws, products = baseline.load_sme_reference(str(ROOT / "open/data"))
        self.assertIn("제7조(중소기업자간 경쟁입찰의 예외 등)", laws)
        self.assertNotIn("제9조(직접생산의 확인 등)", laws)
        rec = record()
        rec["meta"]["세부품명번호목록"] = None
        rec["docs"][0]["text"] = "세부품명번호 1110152201 활성탄 구매"
        before = copy.deepcopy(rec)
        prompt = baseline.build_user_prompt(rec, 16000, products=products)
        self.assertIn("석탄계 입상활성탄 및 석유화학계 활성탄 제외", prompt)
        self.assertIn("1110152201", prompt)
        self.assertEqual(rec, before)
        # A different notice must not inherit a preceding notice's product lookup.
        other = baseline.build_user_prompt(record(), 16000, products=products)
        self.assertNotIn("1110152201", other)
        with tempfile.TemporaryDirectory() as tmp, self.assertRaises(FileNotFoundError):
            baseline.load_sme_reference(tmp)

    def test_product_lookup_distinguishes_codes_names_and_service_candidates(self):
        _, products = baseline.load_sme_reference(str(ROOT / "open/data"))
        rec = record()
        rec["meta"].update(세부품명번호목록="채혈세트[4214269901]", 업무구분="물품(내자)")
        rec["docs"][0]["text"] = "의료용 원심분리기 규격."
        before = copy.deepcopy(rec)
        found = baseline.sme_product_lookup(rec, rec["docs"][0]["text"], products)
        self.assertEqual(found["메타코드_고시미등재"], ["4214269901"])
        self.assertEqual(found["일치후보"][0]["일치출처"], "품명문자열")
        self.assertIn("수처리용", found["일치후보"][0]["특이사항"])
        self.assertEqual(found["서비스보조목록"], [])
        self.assertEqual(rec, before)
        rec["meta"].update(세부품명번호목록="컴퓨터서버[4321150102]", 업무구분="물품(내자)")
        found = baseline.sme_product_lookup(rec, "Arm 서버", products)
        self.assertEqual(found["일치후보"][0]["일치출처"], "메타코드")
        self.assertIn("x86", found["일치후보"][0]["특이사항"])
        self.assertEqual(found["메타코드_고시미등재"], [])
        # An exact metadata match must survive the cap even after many name-only hits.
        names = " ".join([p["세부품명"] for p in products if len(p["세부품명"]) >= 4][:20])
        found = baseline.sme_product_lookup(rec, names, products)
        self.assertEqual(found["일치후보"][0]["세부품명번호"], "4321150102")
        self.assertEqual(len(found["일치후보"]), 12)
        self.assertGreater(found["조회생략행수"], 0)
        rec["meta"].update(세부품명번호목록=None, 업무구분="일반용역")
        found = baseline.sme_product_lookup(rec, "거리문화공연 대행 용역", products)
        self.assertEqual(found["일치후보"], [])
        self.assertTrue(any(p[1] == "기타행사기획및대행서비스"
                            and "10억원 미만" in p[2] for p in found["서비스보조목록"]))
        self.assertFalse(any(p[1] == "상업용오븐" for p in found["서비스보조목록"]))
        found = baseline.sme_product_lookup(rec, "기타행사기획 및 대행서비스 8014199001", products)
        self.assertEqual(found["일치후보"][0]["일치출처"], "문서코드")
        self.assertEqual(found["서비스보조목록"], [])
        found = baseline.sme_product_lookup(rec, "기타행사기획 및 대행서비스", products)
        self.assertTrue(any(p["세부품명번호"] == "8014199001" for p in found["일치후보"]))
        # A match beyond the visible document budget must not leak into the lookup.
        prompt = baseline.build_user_prompt({**record(), "docs": [{"doc_id": "a", "type": "공고문",
                    "text": "가" * 300 + " 1110152201"}]}, 128, products)
        self.assertNotIn("1110152201", prompt)

    def test_diagnostics_preserve_initial_and_retry_metadata(self):
        good = json.dumps(valid())
        runner = object.__new__(baseline.VLLMRunner)
        runner.sp = SimpleNamespace(max_tokens=2048)
        # Exercise logging independently of the split-retry strategy tested above.
        runner.retry_chat = runner.chat
        calls = []
        def chat(batch, **kwargs):
            calls.append(len(batch))
            texts = [good, good[:-2]] if len(calls) == 1 else [""]
            return [SimpleNamespace(outputs=[SimpleNamespace(
                text=text, token_ids=[1] * (2048 if text else 0),
                finish_reason="length" if text else "stop", stop_reason=None)],
                prompt_token_ids=[1, 2, 3]) for text in texts]
        runner.llm = SimpleNamespace(chat=chat)
        events = []
        with self.assertRaisesRegex(RuntimeError, "global_index=129"):
            baseline.run_chunk(runner, [[], []], start=128, ids=["first", "failed"],
                               emit=lambda event, **fields: events.append({"event": event, **fields}))
        responses = [e for e in events if e["event"] == "response"]
        self.assertEqual(calls, [2, 1])
        self.assertEqual([(e["global_index"], e["attempt"]) for e in responses],
                         [(128, 1), (129, 1), (129, 2)])
        self.assertEqual(responses[1]["finish_reason"], "length")
        self.assertEqual(responses[1]["output_tokens"], 2048)
        self.assertEqual(responses[2]["finish_reason"], "stop")
        self.assertEqual(responses[2]["output_tokens"], 0)
        self.assertEqual(responses[2]["id"], "failed")
        self.assertNotIn("response_text", json.dumps(events))
        self.assertNotIn(good, json.dumps(events))
        events.clear()
        runner.llm.chat = lambda batch, **kw: [SimpleNamespace(outputs=[SimpleNamespace(
            text=good, token_ids=[1], finish_reason="stop", stop_reason=None)], prompt_token_ids=[1])]
        baseline.run_chunk(runner, [[]], debug_responses=True,
                           emit=lambda event, **kw: events.append(kw))
        self.assertEqual(events[0]["response_text"], good)
        # A call exception must not inherit completion metadata from the previous call.
        def broken(*args, **kwargs):
            raise ValueError("runtime failure")
        runner.llm.chat = broken
        events.clear()
        with self.assertRaisesRegex(RuntimeError, "runtime failure"):
            baseline.run_chunk(runner, [[]], emit=lambda event, **kw: events.append(kw))
        self.assertTrue(all("finish_reason" not in e for e in events))

    def test_failed_run_leaves_diagnostics_and_no_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "submission.csv"
            class Broken(baseline.MockRunner):
                def chat(self, batch):
                    raise ValueError("test runtime cause")
            with self.assertRaisesRegex(RuntimeError, "test runtime cause"):
                baseline.run(str(ROOT / "open/data/test.jsonl.gz"), str(out), Broken,
                             limit=1, chunk=128, max_chars=16000, data_dir=str(ROOT / "open/data"))
            path = out.with_name("diagnostics.jsonl")
            events = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(events[0]["event"], "run_started")
            self.assertEqual(events[-1]["event"], "run_failed")
            self.assertIn("test runtime cause", events[-1]["traceback"])
            self.assertFalse(out.exists())
            self.assertFalse(out.with_name("run_report.json").exists())
            raw = path.read_bytes()
            with self.assertRaises(ValueError):
                baseline.run(str(ROOT / "open/data/test.jsonl.gz"), str(out), Broken,
                             limit=1, chunk=128, max_chars=16000, data_dir=str(ROOT / "open/data"))
            self.assertEqual(path.read_bytes(), raw)
            command = [sys.executable, "-X", "utf8", str(ROOT / "script.py"),
                       "--data-dir", str(ROOT / "open/data"), "--model-dir", str(Path(tmp) / "missing-model"),
                       "--output-dir", str(Path(tmp) / "load-failed")]
            failed = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", timeout=30)
            self.assertEqual(failed.returncode, 1)
            self.assertIn("Traceback", failed.stderr)
            load_events = [json.loads(line) for line in
                           (Path(tmp) / "load-failed/diagnostics.jsonl").read_text(encoding="utf-8").splitlines()]
            self.assertEqual(load_events[-1]["event"], "run_failed")
            self.assertIn("로컬 디렉터리", load_events[-1]["error_message"])
            self.assertIn("items", load_events[1]["sha256"])

    def test_missing_or_ambiguous_output_is_rejected(self):
        obj = valid()
        for value in (0.5, 2, -1, "unknown", "2", "", [], {}, None):
            with self.subTest(value=value):
                bad = copy.deepcopy(obj)
                bad["v1"]["위반여부"] = value
                with self.assertRaises(ValueError):
                    baseline.parse_judgment(json.dumps(bad))
        for text in ("", "{}", "[]", '{"v1":', json.dumps({k: v for k, v in obj.items() if k != "v24"})):
            with self.subTest(text=text[:30]), self.assertRaises(ValueError):
                baseline.parse_judgment(text)
        self.assertEqual(baseline.parse_judgment(json.dumps(obj))[0], obj)
        # Gemma thought text must never supply an answer when the final JSON is absent.
        thought = '<|channel>thought\n' + json.dumps(obj) + '<channel|>'
        with self.assertRaises(ValueError):
            baseline.parse_judgment(thought)
        self.assertEqual(baseline.parse_judgment(thought + json.dumps(obj))[0], obj)

    def test_budget_is_hard_limit(self):
        class TooLarge:
            def count_tokens(self, messages):
                return 20000
        with self.assertRaises(ValueError):
            baseline.fit_to_budget(record(), "system", TooLarge(), 2000, budget=100)
        class Counter:
            def count_tokens(self, messages):
                return sum(len(m["content"]) for m in messages)
        rec = record()
        rec["docs"][0]["text"] = "가" * 5000
        _, count, _ = baseline.fit_to_budget(rec, "system", Counter(), 4000, budget=1500)
        self.assertLessEqual(count, 1500)

    def test_failed_model_never_becomes_zero_success(self):
        class Broken:
            def chat(self, batch):
                raise RuntimeError("simulated model failure")
        with self.assertRaises(RuntimeError):
            baseline.run_chunk(Broken(), [[{"role": "user", "content": "공고"}]])
        class Retry:
            calls = []
            def chat(self, batch):
                self.calls.append(len(batch))
                return [json.dumps(valid()), ""] if len(batch) == 2 else [json.dumps(valid())]
        runner = Retry()
        self.assertEqual(len(baseline.run_chunk(runner, [[], []])), 2)
        self.assertEqual(runner.calls, [2, 1])

    def test_attachment_and_observability(self):
        rec = record()
        rec["docs"].append({"doc_id": "b", "type": "과업지시서", "text": "첨부의중요조건" * 1000})
        context = baseline.build_context(rec, 1000)
        self.assertIn("첨부의중요조건", context)
        self.assertIn("Truncated", context)
        prompt = baseline.build_user_prompt(rec, 1000)
        self.assertIn("완전관측", prompt)
        self.assertIn("false", prompt)
        self.assertIn("null", prompt)
        self.assertEqual(rec["docs"][1]["text"], "첨부의중요조건" * 1000)

    def test_evidence_does_not_cross_documents(self):
        rec = record()
        rec["docs"][0]["text"] = '첫째문서'
        rec["docs"].append({"doc_id": "b", "type": "규격서", "text": '둘째문서, "인용"'})
        obj = valid()
        obj["v1"] = {"위반여부": 1, "근거문구": "첫째문서\n둘째문서"}
        self.assertEqual(baseline.postprocess(obj, rec)["v1"]["근거문구"], "")
        obj["v1"]["근거문구"] = '둘째문서, "인용"'
        self.assertEqual(baseline.postprocess(obj, rec)["v1"]["근거문구"], '둘째문서, "인용"')
        schema = baseline.decode_schema(str(ROOT / "open/data"))
        self.assertEqual(schema["properties"]["v1"]["properties"]["근거문구"]["maxLength"], 500)

    def test_both_quote_gates_restore_spacing_before_judging(self):
        """줄바꿈이 공백으로 눌린 정확한 인용을 미검증으로 떨어뜨리지 않는다.

        `_company_size_bands()` 와 `verify_document_requirements()` 가 각자 `quoted()` 를
        갖는데, 한쪽만 `restore_spacing()` 을 부르면 같은 인용을 다르게 판정한다.
        실제로 `PPS-DEV-043`·`PPS-DEV-22` 가 그래서 `unverified_qualification` 으로 막혔다.
        모델이 틀린 것이 아니라 게이트가 옆의 복원기를 안 쓴 것이다.
        """
        rec = record()
        rec["docs"][0]["text"] = "가. 참가자격\n\n제한 없음"
        visible = baseline.build_context(rec, 16000)
        # 모델이 내는 모양 — 줄바꿈이 공백 하나로 눌려 있다.
        pressed = "가. 참가자격 제한 없음"
        self.assertNotIn(pressed, visible)                       # 날문자열로는 못 찾는다
        restored = baseline.restore_spacing(pressed, rec, visible)
        self.assertTrue(restored and restored in visible)        # 복원기는 찾아낸다

        import inspect
        for owner in (baseline._company_size_bands, baseline.verify_document_requirements):
            self.assertIn("restore_spacing", inspect.getsource(owner),
                          f"{owner.__name__} 의 인용 검사가 복원기를 부르지 않는다")

    def test_violation_without_a_verified_quote_is_lowered(self):
        """D4-4 가 e 를 원문의 연속된 부분문자열로 규정한다. 한 구절도 못 집는 위반은 못 선다.

        부재탐지 5항목은 스키마가 근거문구를 null 로 고정하므로 빈칸이 규정된 모양이고,
        v24 는 대조형이라 한 구절로 안 잡히는 것이 정상이라 둘 다 예외다.
        """
        def judged(item, quote):
            rec = record()
            rec["docs"][0]["text"] = "앞 문장. 공고에 실제로 있는 구절. 뒤 문장."
            obj = valid()
            obj[item] = {"위반여부": 1, "근거문구": quote}
            return baseline.postprocess(obj, rec)[item]["위반여부"]

        # 근거가 없거나 원문에 없는 인용이면 위반이 안 선다.
        self.assertEqual(judged("v1", None), 0)
        self.assertEqual(judged("v1", ""), 0)
        self.assertEqual(judged("v1", "공고 어디에도 없는 문장"), 0)
        # 원문에 있는 인용이면 그대로 선다.
        self.assertEqual(judged("v1", "공고에 실제로 있는 구절"), 1)
        # 예외 둘. 부재탐지는 빈 근거가 규정된 모양이라 그대로 선다.
        self.assertEqual(judged("v20", None), 1)
        # v24 는 근거 계약에서 빠지지만 대신 대조 검사를 받는다 — 코드가 공고와 등록값의
        # 불일치를 하나도 못 찾으면 근거가 있든 없든 내려간다.
        self.assertIn("v24", baseline.EVIDENCE_EXEMPT)
        self.assertFalse(set(baseline.EVIDENCE_EXEMPT) & set(baseline.ABSENCE))
        self.assertEqual(judged("v24", None), 0)            # 불일치 없음 → 내려간다

        def judged_v24(text, meta):
            rec = record()
            rec["docs"][0]["text"] = text
            rec["meta"].update(meta)
            obj = valid()
            obj["v24"] = {"위반여부": 1, "근거문구": None}
            return baseline.postprocess(obj, rec)["v24"]["위반여부"]

        # 본문은 업종을 거는데 등록은 제한 없음 — 대조로 설명되는 불일치다. 근거가 비어도 선다.
        self.assertEqual(judged_v24("입찰참가자격 업종코드 1169 보유 업체",
                                    {"업종제한여부": "N"}), 1)
        # 같은 본문이라도 등록이 그 코드를 제한으로 갖고 있으면 불일치가 아니다.
        self.assertEqual(judged_v24("입찰참가자격 업종코드 1169 보유 업체",
                                    {"업종제한여부": "Y", "면허업종제한목록": "(1169)"}), 0)

    def test_evidence_that_refutes_the_item_lowers_only_that_item(self):
        def judged(item, quote, text=None, meta=None):
            rec = record()
            rec["docs"][0]["text"] = text or f"앞 문장. {quote} 뒤 문장."
            rec["meta"].update(meta or {})
            obj = valid()
            obj[item] = {"위반여부": 1, "근거문구": quote}
            obj["v1"] = {"위반여부": 1, "근거문구": quote}
            out = baseline.postprocess(obj, rec)
            self.assertEqual(out["v1"]["위반여부"], 1)  # 다른 항목은 그대로
            return out[item]["위반여부"]

        # v19는 인용이 아니라 **공고가 무엇을 요구했는지**를 먼저 본다.
        # [items](docs/items.md) 확정 해석: 위반은 입찰·투찰 단계에서 확약서를 요구한 경우다.
        self.assertEqual(judged("v19", "계약 시 확약서를 발급받아 제출하여야 합니다."), 0)
        self.assertEqual(judged("v19", "낙찰자 결정 후 협약서를 발급받아야 합니다."), 0)
        self.assertEqual(judged("v19", "확약서를 전자입찰서 제출 마감일 전까지 보유하여야 하고, "
                                       "계약 시 제출해야 합니다."), 1)
        # 제출서류 목록 한 줄만 있고 공고 어디에도 입찰 단계 요구가 없으면 위반이 아니다.
        # dev 오탐 15건 중 다수가 정확히 이 모양이었다.
        self.assertEqual(judged("v19", "물품공급 확약서 1부"), 0)
        # 같은 공고에 입찰 단계 요구가 있으면, 모델이 목록 한 줄을 인용했어도 위반이다.
        self.assertEqual(judged("v19", "물품공급 확약서 1부",
                                text="확약서는 전자입찰서 제출 마감일 전일까지 보유하여야 합니다. "
                                     "제출서류: 물품공급 확약서 1부"), 1)
        # 요구가 있어도 그 인용이 계약 시 의무만 말하면 그 인용은 근거가 아니다.
        self.assertEqual(judged("v19", "계약 시 반드시 제출하여야 한다.",
                                text="확약서는 입찰 전까지 보유하여야 합니다. "
                                     "계약 시 반드시 제출하여야 한다."), 0)
        # v21: 공동계약 불허나 하한 이상 지분은 내리고, 하한 미만 지분은 둔다.
        self.assertEqual(judged("v21", "공동수급은 허용하지 않습니다."), 0)
        self.assertEqual(judged("v21", "구성원별 최소지분율은 10% 이상이어야 합니다."), 0)
        self.assertEqual(judged("v21", "구성원별 최소 지분율은 5% 이상으로 하여야 함"), 1)
        self.assertEqual(judged("v21", "업체별 최소 지분율은 2% 이상"), 1)
        # **하한은 계약법과 공동도급 방식이 정한다.** 항목명 "공동 5% (10%)"가 그것이다.
        # 지방 집행기준 제6장 제2절 1-나-2)는 5% 이상, 국가 공동계약운용요령 ⑤나는 10% 이상이다.
        # 하한을 10 하나로 두면 지방의 정상인 5%를 전부 위반으로 남긴다 — dev 오탐 10건의 정체다.
        local = {"적용계약법": "지방자치단체를 당사자로 하는 계약에 관한 법률"}
        self.assertEqual(judged("v21", "구성원별 최소 지분율은 5% 이상으로 하여야 함", meta=local), 0)
        self.assertEqual(judged("v21", "업체별 최소 지분율은 3% 이상", meta=local), 1)
        # 같은 절 3): 분담이행방식은 최소지분율을 적용하지 않는다.
        self.assertEqual(judged("v21", "업체별 최소 지분율은 3% 이상",
                                meta={**local, "공동도급구성방식": "분담이행"}), 0)
        # "단독"만으로는 내리지 않는다(특수관계인 지분 조항 등).
        self.assertEqual(judged("v21", "단독으로 또는 합산하여 발행주식 총수의 100분의 30 이상"), 1)
        # v24 는 인용 검사와 대조 검사를 함께 받는다. 인용이 메타와 일치하면 내리고,
        # 일치하지 않더라도 **코드가 축에서 불일치를 하나도 못 찾으면** 내린다.
        # 그래서 `judged("v24", ...)` 의 1 은 "이 인용이 어긋난다" 가 아니라
        # "어긋나고, 그 어긋남을 코드도 축에서 확인했다" 는 뜻이다.
        meta = {"배정예산금액": 30000000, "입찰추정가격": 27272727, "계약방법": "제한경쟁",
                "지역제한여부": "Y", "제한지역코드목록": "경상남도"}
        self.assertEqual(judged("v24", "입찰금액 : 30,000,000원(부가세포함)", meta=meta), 0)
        self.assertEqual(judged("v24", "지역제한(경상남도)", meta=meta), 0)
        self.assertEqual(judged("v24", "지역제한(경상남도, 부산광역시)", meta=meta), 1)
        self.assertEqual(judged("v24", "행사 용역(제한경쟁·3억원미만)", meta=meta), 0)
        self.assertEqual(judged("v24", "행사 용역(일반경쟁·3억원미만)", meta=meta), 1)
        self.assertEqual(judged("v24", "행사 용역(제한경쟁·1천만원미만)", meta=meta), 1)
        # 금액만 어긋나는 인용은 이제 내려간다. 예산 축이 `DISABLED_AXES` 로 꺼져 있어
        # 코드가 그 어긋남을 확인해 주지 못하기 때문이다 — 그 축이 세 라운드 연속으로
        # 부가세·산식 구성값·표시 반올림을 불일치로 읽었다. 의도된 교환이다.
        self.assertIn("예산", baseline.DISABLED_AXES)
        self.assertEqual(judged("v24", "용역금액: 금37,930,000원", meta=meta), 0)
        # v9: 곁에 동등품 허용이 있거나 사양 하한이면 내리고, 모델명만이면 둔다.
        self.assertEqual(judged("v9", "형식명 : ABC-100",
                                text="형식명 : ABC-100 (동등 이상의 제품 가능)"), 0)
        self.assertEqual(judged("v9", "CPU i5-14500 프로세서 이상"), 0)
        self.assertEqual(judged("v9", "제조사·모델명 : ABC 터보젯"), 1)
        self.assertEqual(judged("v9", "형식명 : ABC-100",
                                text="형식명 : ABC-100 과 호환되어야 함"), 1)
        # 곁의 "상당"은 대개 금액 뜻이라 동등품 허용으로 읽지 않는다.
        self.assertEqual(judged("v9", "형식명 : ABC-100",
                                text="형식명 : ABC-100 1대 (부가세 상당액 포함)"), 1)

        # 근거가 비었거나 원문에 없는 양성은 내린다 — D4-4 의 근거 계약이고
        # test_violation_without_a_verified_quote_is_lowered 가 그 규칙을 소유한다.
        # 여기서는 evidence_refutes 가 못 본 자리도 같은 계약에 걸린다는 것만 본다.
        # v24 는 그 계약에서 빠지지만 대조 검사가 대신 받는다 — 이 기록에는 축이 찾을
        # 불일치가 없으므로 결국 같이 내려간다. 네 자리 모두 0 인 이유가 서로 다르다.
        rec = record()
        obj = valid()
        for item in ("v9", "v19", "v21", "v24"):
            obj[item] = {"위반여부": 1, "근거문구": None}
        obj["v21"]["근거문구"] = "원문에 없는 공동수급 불가"
        out = baseline.postprocess(obj, rec)
        self.assertEqual([out[i]["위반여부"] for i in ("v9", "v19", "v21", "v24")], [0, 0, 0, 0])

    def test_scope_gates_lower_only_the_out_of_scope_positives(self):
        """v3·v4·v5·v6 의 적용범위 게이트. 내리는 자리와 **안 내리는 자리**를 함께 고정한다."""
        def judged(item, quote, text=None, meta=None):
            rec = record()
            rec["docs"][0]["text"] = text or f"앞 문장. {quote} 뒤 문장."
            rec["meta"].update(meta or {})
            obj = valid()
            obj[item] = {"위반여부": 1, "근거문구": quote}
            obj["v1"] = {"위반여부": 1, "근거문구": quote}
            out = baseline.postprocess(obj, rec)
            self.assertEqual(out["v1"]["위반여부"], 1)  # 다른 항목은 그대로
            return out[item]["위반여부"]

        # ----- v3: 배수는 **인용 안에서** 읽는다. 조문은 1배 이내를 허용한다.
        small = {"입찰추정가격": 89_090_909}
        self.assertEqual(judged("v3", "5년 이내 용역 실적이 3천만원 이상인 업체", meta=small), 0)
        # 같은 인용인데 본문에 더 큰 금액이 따로 있어도 판단은 인용을 따른다.
        # 문서 최댓값을 집던 옛 코드가 여기서 배수 1.12 를 읽어 오탐을 살렸다.
        self.assertEqual(judged("v3", "5년 이내 용역 실적이 3천만원 이상인 업체",
                                text="총 사업비는 1억원이다. 5년 이내 용역 실적이 3천만원 이상인 업체",
                                meta=small), 0)
        # **비율 표기로는 내리지 않는다.** 한 인용 안에서 어느 비율이 실적 요구인지 가릴
        # 방법을 못 세웠다 — 세 번 시도했고 세 번 다 정탐을 지웠다(리뷰 P1 세 라운드).
        # 아래 다섯은 전부 **양성 보존**이고, 그 이유가 서로 다르다.
        self.assertEqual(judged("v3", "실적 3억원 이상 (부가세 10% 포함)",
                                meta={"입찰추정가격": 100_000_000}), 1)      # 곁의 부가세율
        for joiner in (", ", ". ", "로서 "):                                 # 구분자만 바뀐 같은 문장
            self.assertEqual(judged("v3", "유사용역 실적 3억원 이상인 업체" + joiner +
                                          "입찰보증금은 사업비의 5% 이상 납부",
                                    meta={"입찰추정가격": 100_000_000}), 1)
        self.assertEqual(judged("v3", "유사사업 수행실적 예산금액의 100% 이상",
                                meta={"입찰추정가격": 56_202_727}), 1)        # 금액이 없다
        self.assertEqual(judged("v3", "가. 입찰 금액의 100% 이상",
                                meta={"입찰추정가격": 147_905_232}), 1)       # 실적도 금액도 없다
        # 금액과 비율이 같이 있으면 **금액으로** 판정한다. 1배 이상이면 그대로 둔다.
        self.assertEqual(judged("v3", "단일 건으로 455,000,000원 이상(기초금액의 130% 이상)의 실적",
                                meta={"입찰추정가격": 318_181_818}), 1)
        # 1배 이상을 요구하는 인용은 그대로 둔다.
        self.assertEqual(judged("v3", "단일 건 3억 원 이상의 유사사업 실적",
                                meta={"입찰추정가격": 227_272_727}), 1)
        # 근거가 비면 내린다. 근거 계약이 먼저 걸리므로 함수 자체로 확인한다.
        self.assertEqual(baseline.performance_below_budget({"meta": small}, ""), 0.0)
        # 기준액이나 금액을 못 읽으면 내리지 않는다 — 모르는 것을 근거로 내리지 않는다.
        self.assertIsNone(baseline.performance_below_budget({"meta": {}}, "실적 3천만원"))
        self.assertIsNone(baseline.performance_below_budget({"meta": small}, "실적이 있는 업체"))

        # ----- v4: 검출기의 미탐은 "기관 제한이 없다"가 아니다. 0을 1로만 올린다.
        institution = "가. 입찰참가자격: 최근 3년 이내 공공기관에서 발주한 유사용역 실적이 있는 업체"
        self.assertEqual(judged("v4", institution), 1)
        # 익명화된 기관 토큰은 검출기 어휘 밖이라 None 이 나온다. 그것으로 모델 양성을
        # 내리면 정답까지 지운다 — 한때 그렇게 했다가 리뷰 P1 으로 되돌렸다.
        anonymous = "입찰참가자격: [수요기관(기초자치단체)|지역=r1]이 발주한 유사용역 실적을 보유한 업체"
        self.assertIsNone(baseline.detect_institution_performance(
            {"docs": [{"doc_id": "a", "type": "공고문", "text": anonymous}]}))
        self.assertEqual(judged("v4", anonymous), 1)

        # ----- v5: 고시금액 경계는 계약법·업무구분마다 다르다(REGION_PRICE_LIMIT).
        region = "주된 영업소가 서울특별시 관내에 있는 업체"
        local = {"적용계약법": "지방계약법", "업무구분": "일반용역"}
        self.assertEqual(judged("v5", region, meta={**local, "입찰추정가격": 262_727_273}), 0)
        self.assertEqual(judged("v5", region, meta={**local, "입찰추정가격": 555_308_000}), 1)
        national = {"적용계약법": "국가계약법", "업무구분": "일반용역"}
        self.assertEqual(judged("v5", region, meta={**national, "입찰추정가격": 200_000_000}), 0)
        self.assertEqual(judged("v5", region, meta={**national, "입찰추정가격": 727_272_727}), 1)
        # **판단할 수 없으면 반증이 아니다.** `region_restriction_allowed()` 는 v7 을 지키려고
        # 모르면 True(= 못 막는다)를 내는데, 그것을 "위반이 아니다"로 읽으면 판단 불가인
        # 공고의 v5 양성을 지운다(리뷰 P1). 세 가지 불명 모두에서 양성이 서 있어야 한다.
        self.assertEqual(judged("v5", region, meta={**national, "입찰추정가격": None}), 1)
        self.assertEqual(judged("v5", region, meta={"적용계약법": None, "업무구분": "일반용역",
                                                    "입찰추정가격": 727_272_727}), 1)
        self.assertEqual(judged("v5", region, meta={"적용계약법": "국가계약법", "업무구분": None,
                                                    "입찰추정가격": 727_272_727}), 1)
        # **v7 은 같은 표를 다른 방향으로 쓴다.** 고시금액 미만은 v7 의 구간이므로
        # v5 를 내리는 그 기록에서 v7 은 그대로 서 있어야 한다.
        self.assertEqual(judged("v7", region, meta={**local, "입찰추정가격": 262_727_273}), 1)

        # ----- v6: 근거가 시·군·구 제한을 가리켜야 한다.
        basic = "주된 영업소가 서울특별시 [지역:r1|단위=기초|광역=서울특별시] 내에 있는 업체"
        self.assertEqual(judged("v6", basic), 1)
        self.assertEqual(judged("v6", "본 입찰은 전자입찰로만 집행합니다."), 0)
        self.assertEqual(judged("v6", "서울특별시 또는 경기도에 소재한 업체"), 0)
        # **기초 단위를 이름으로만 적은 인용도 지역제한이다.** 광역명도 익명화 토큰도 없다는
        # 이유로 내리면 시·군·구 제한 정탐을 잃는다(리뷰 P1). 이름 뒤에는 조사가 붙는다.
        self.assertEqual(judged("v6", "주된 영업소가 고양시에 있는 업체"), 1)
        self.assertEqual(judged("v6", "본점 소재지가 성남시의 관내인 업체"), 1)
        # 두 음절 이상을 앞에 요구하므로 `실시`·`고시` 같은 낱말은 기초 단위로 세지 않는다.
        self.assertEqual(judged("v6", "본 용역은 2026년 3월에 실시에 들어갑니다."), 0)

    def test_mock_cli_and_invalid_inputs(self):
        with tempfile.TemporaryDirectory(prefix="t1 한글 ") as tmp:
            tmp = Path(tmp)
            env = {**os.environ, "PPS_DATA_DIR": str(ROOT / "open/data"),
                   "PPS_OUTPUT_DIR": str(tmp / "output")}
            command = [sys.executable, "-X", "utf8", str(ROOT / "script.py"), "--mock"]
            success = subprocess.run(command, env=env, cwd=tmp, capture_output=True, timeout=30)
            self.assertEqual(success.returncode, 0, success.stderr.decode("utf-8"))
            output = tmp / "output/submission.csv"
            raw = output.read_bytes()
            self.assertFalse(raw.startswith(b"\xef\xbb\xbf"))
            self.assertNotIn(b"\r", raw)
            with output.open(encoding="utf-8", newline="") as f:
                rows = list(csv.reader(f))
            self.assertEqual(rows[0], baseline.COLUMNS)
            self.assertEqual(len(rows), 11)
            report = json.loads((tmp / "output/run_report.json").read_text(encoding="utf-8"))
            self.assertEqual(report["mode"], "mock")
            self.assertEqual(report["model_success_count"], 0)
            self.assertIsNone(report["model"])
            # 기록에 사용자·기계 이름이 드러나는 절대 경로를 남기지 않는다. 실제 입출력은 그대로다.
            self.assertEqual(report["출력"], "<외부>/submission.csv")
            self.assertEqual(report["reproduction"]["settings"]["data_dir"], "open/data")
            self.assertEqual(report["reproduction"]["settings"]["output"], "<외부>/submission.csv")
            self.assertEqual(report["reproduction"]["argv"][0], "script.py")
            for name in ("run_report.json", "diagnostics.jsonl"):
                text = (tmp / "output" / name).read_text(encoding="utf-8")
                found = re.search(r"[A-Za-z]:[\\/](?!/)|/(?:Users|home)/", text)
                self.assertIsNone(found, f"{name}: {found.group(0) if found else ''}")
                self.assertNotIn(tmp.as_posix(), text)
            # Reject reusing old success, including after a failing run.
            repeated = subprocess.run(command, env=env, cwd=tmp, capture_output=True, timeout=30)
            self.assertNotEqual(repeated.returncode, 0)
            self.assertEqual(output.read_bytes(), raw)
            source = tmp / "input.jsonl"
            for name, text in [("empty", ""), ("duplicate", (json.dumps(record()) + "\n") * 2)]:
                source.write_text(text, encoding="utf-8")
                env["PPS_OUTPUT_DIR"] = str(tmp / name)
                failed = subprocess.run(command + ["--input", str(source)], env=env, cwd=tmp,
                                        capture_output=True, timeout=30)
                self.assertNotEqual(failed.returncode, 0)
                self.assertFalse((tmp / name / "submission.csv").exists())

    def test_csv_and_template_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "submission.csv"
            path.write_text(",".join(baseline.COLUMNS) + "\n\n", encoding="utf-8")
            self.assertTrue(baseline.validate_csv(str(path), ["sample"]))
            row = baseline.to_row("sample", baseline.postprocess(valid(), record()))
            row["e1"] = "비위반근거"
            baseline.write_csv([row], str(path))
            self.assertTrue(baseline.validate_csv(str(path), ["sample"]))
            row["v1"] = 1
            row["e1"] = '원문, "인용"\n다음 줄'
            baseline.write_csv([row], str(path))
            self.assertEqual(baseline.validate_csv(str(path), ["sample"]), [])
            with path.open(encoding="utf-8", newline="") as f:
                self.assertEqual(list(csv.DictReader(f))[0]["e1"], row["e1"])
        class Tokenizer:
            def apply_chat_template(self, messages, **kwargs):
                assert kwargs.get("enable_thinking") is False
                return {"input_ids": [1, 2, 3]}
        runner = object.__new__(baseline.VLLMRunner)
        runner.tok = Tokenizer()
        self.assertEqual(runner.count_tokens([]), 3)


if __name__ == "__main__":
    unittest.main()
