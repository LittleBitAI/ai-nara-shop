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
                    if items is not None:   # N3 경쟁제품 호출은 facts 없이 두 칸만 낸다
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
                # 합동 1회 → v13 추가 호출(선택 공고가 있을 때만) → N3 경쟁제품 호출(전건).
                self.assertEqual(calls, [(None, 4)] + [(["v13"], 2)] * bool(positives)
                                 + [(baseline.PRODUCT_ITEMS, 4)])
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
                outputs = []
                for messages in batch:
                    if items is None:
                        self_test.assertEqual(messages[0]["content"], expected_system)
                        self_test.assertNotIn("[Provided 고시", messages[1]["content"])
                    else:
                        self_test.assertEqual(items, ["v13"])
                        self_test.assertNotIn("- v24:", messages[0]["content"])
                        self_test.assertIn("[Provided 고시", messages[1]["content"])
                    obj = {k: {"위반여부": 1, "근거문구": None} for k in (items or baseline.ITEMS)}
                    if items is not None:
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
            self.assertEqual(calls[:2], [None, ["v13"]])
            # 나머지는 N3 경쟁제품 호출뿐이다. 다른 항목 목록이 오면 실패한다.
            self.assertTrue(all(c == baseline.PRODUCT_ITEMS for c in calls[2:]), calls)
            with out.open(encoding="utf-8") as f:
                final = list(csv.DictReader(f))
            with out.with_name("baseline_submission.csv").open(encoding="utf-8") as f:
                original = list(csv.DictReader(f))
            for before, after in zip(original, final):
                self.assertEqual(before["v13"], "1")
                self.assertEqual(after["v13"], "0")
                for col in baseline.COLUMNS:
                    if col not in ["v13", "e13"]:
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

        # v19: 계약 시·낙찰 후 제출만이면 내리고, 입찰 단계 보유 요구가 같이 있으면 둔다.
        self.assertEqual(judged("v19", "계약 시 확약서를 발급받아 제출하여야 합니다."), 0)
        self.assertEqual(judged("v19", "낙찰자 결정 후 협약서를 발급받아야 합니다."), 0)
        self.assertEqual(judged("v19", "확약서를 전자입찰서 제출 마감일 전까지 보유하여야 하고, "
                                       "계약 시 제출해야 합니다."), 1)
        self.assertEqual(judged("v19", "물품공급 확약서 1부"), 1)
        # v21: 공동계약 불허나 10% 이상 지분은 내리고, 10% 미만 지분은 둔다.
        self.assertEqual(judged("v21", "공동수급은 허용하지 않습니다."), 0)
        self.assertEqual(judged("v21", "구성원별 최소지분율은 10% 이상이어야 합니다."), 0)
        self.assertEqual(judged("v21", "구성원별 최소 지분율은 5% 이상으로 하여야 함"), 1)
        self.assertEqual(judged("v21", "업체별 최소 지분율은 2% 이상"), 1)
        # "단독"만으로는 내리지 않는다(특수관계인 지분 조항 등).
        self.assertEqual(judged("v21", "단독으로 또는 합산하여 발행주식 총수의 100분의 30 이상"), 1)
        # v24: 같은 뜻의 메타 값과 일치할 때만 내린다.
        meta = {"배정예산금액": 30000000, "입찰추정가격": 27272727, "계약방법": "제한경쟁",
                "지역제한여부": "Y", "제한지역코드목록": "경상남도"}
        self.assertEqual(judged("v24", "입찰금액 : 30,000,000원(부가세포함)", meta=meta), 0)
        self.assertEqual(judged("v24", "용역금액: 금37,930,000원", meta=meta), 1)
        self.assertEqual(judged("v24", "지역제한(경상남도)", meta=meta), 0)
        self.assertEqual(judged("v24", "지역제한(경상남도, 부산광역시)", meta=meta), 1)
        self.assertEqual(judged("v24", "행사 용역(제한경쟁·3억원미만)", meta=meta), 0)
        self.assertEqual(judged("v24", "행사 용역(일반경쟁·3억원미만)", meta=meta), 1)
        self.assertEqual(judged("v24", "행사 용역(제한경쟁·1천만원미만)", meta=meta), 1)
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

        # 근거가 비었거나 원문에 없는 양성은 근거만으로 내리지 않는다.
        rec = record()
        obj = valid()
        for item in ("v9", "v19", "v21", "v24"):
            obj[item] = {"위반여부": 1, "근거문구": None}
        obj["v21"]["근거문구"] = "원문에 없는 공동수급 불가"
        out = baseline.postprocess(obj, rec)
        self.assertEqual([out[i]["위반여부"] for i in ("v9", "v19", "v21", "v24")], [1, 1, 1, 1])

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
