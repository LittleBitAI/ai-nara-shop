"""A1 결정표·실패 보존·한 번 추출·재생 계약. 모델 성능 검사가 아니다."""

import copy
import csv
import gzip
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

from tests.test_baseline import baseline as script, valid


def notice(price=150_000_000):
    return {
        "id": "arbitrary-id", "meta": {"입찰추정가격": price, "업무구분": "물품(내자)"},
        "docs": [{"doc_id": "a", "type": "공고문", "text": (
            "일반 의료기기 구매. 입찰참가자격: 소기업 또는 소상공인인 업체. "
            "중소기업자로서 확인서를 소지한 업체. 사업자등록 업체 누구나 참가 가능. "
            "우선조달 예외 사유: 비영리법인의 참여가 필요한 연구용역. "
            "유자격 소기업이 3인 이하이므로 중소기업으로 확대한다. "
            "조합과 3인 이상의 제조 소기업이 수행한 공동사업 제품 구매.") }],
        "input_completeness": {"완전관측": True}, "dropped_doc_counts": {},
    }


def facts(qualification="small_only"):
    quotes = {"small_only": "소기업 또는 소상공인인 업체.",
              "sme_allowed": "중소기업자로서 확인서를 소지한 업체.",
              "unrestricted": "사업자등록 업체 누구나 참가 가능.", "unknown": None}
    return dict(scope="general", scope_quote="일반 의료기기 구매.",
                qualification=qualification, qualification_quote=quotes[qualification],
                qualification_complete="yes", priority_exception="no", priority_exception_quote=None,
                size_exception="none", size_exception_quote=None)


class CompanySizeTests(unittest.TestCase):
    def test_table_and_exact_boundaries(self):
        table = {
            99_999_999: ("v18", None, "v17"),
            100_000_000: ("v16", "v15", None),
            229_999_999: ("v16", "v15", None),
            230_000_000: (None, "v14", "v14"),
        }
        for price, expected in table.items():
            for qualification, hit in zip(("unrestricted", "small_only", "sme_allowed"), expected):
                with self.subTest(price=price, qualification=qualification):
                    out, reason = script.verify_company_size(facts(qualification), notice(price), 16000)
                    self.assertEqual([v for v, c in out.items() if c["위반여부"]], [hit] if hit else [])
                    self.assertEqual(set(out), set(script.BAND_ITEMS))
                    for v in ("v16", "v18"):
                        self.assertIsNone(out[v]["근거문구"])

    def test_exception_scope_and_uncertainty(self):
        for price, qualification, field, value, quote, expected in [
            (150_000_000, "unrestricted", "priority_exception", "yes",
             "우선조달 예외 사유: 비영리법인의 참여가 필요한 연구용역.", None),
            (50_000_000, "unrestricted", "priority_exception", "yes",
             "우선조달 예외 사유: 비영리법인의 참여가 필요한 연구용역.", None),
            # 비영리법인 예외가 영리기업의 과도한 소기업 제한까지 정당화하지 않는다.
            (150_000_000, "small_only", "priority_exception", "yes",
             "우선조달 예외 사유: 비영리법인의 참여가 필요한 연구용역.", "v15"),
            (50_000_000, "sme_allowed", "size_exception", "broaden_sme",
             "유자격 소기업이 3인 이하이므로 중소기업으로 확대한다.", None),
            (150_000_000, "small_only", "size_exception", "joint_small",
             "조합과 3인 이상의 제조 소기업이 수행한 공동사업 제품 구매.", None),
        ]:
            f = facts(qualification)
            f[field], f[field + "_quote"] = value, quote
            out, _ = script.verify_company_size(f, notice(price), 16000)
            self.assertEqual([v for v, c in out.items() if c["위반여부"]], [expected] if expected else [])
        f = facts()
        f.update(size_exception="joint_small", size_exception_quote="조합과 3인 이상의 제조 소기업이 수행한 공동사업 제품 구매.")
        self.assertEqual(script.verify_company_size(f, notice(250_000_000), 16000)[0], {})
        for field, value in [("qualification", "unknown"), ("scope", "unknown"),
                             ("qualification_quote", "원문에 없는 인용"),
                             ("size_exception", "unknown")]:
            f = facts()
            f[field] = value
            out, _ = script.verify_company_size(f, notice(), 16000)
            self.assertEqual(out, {})  # 판단 불가를 합동 판정 덮어쓰기에 쓰지 않는다.
        for price in (None, True, float("nan"), float("inf")):
            out, _ = script.verify_company_size(facts(), notice(price), 16000)
            self.assertEqual(out, {})

    def test_missing_documents_do_not_prove_absence(self):
        for change in ("incomplete", "dropped", "truncated", "unobserved"):
            rec, f = notice(), facts("unrestricted")
            if change == "incomplete":
                rec["input_completeness"]["완전관측"] = False
            elif change == "dropped":
                rec["dropped_doc_counts"] = {"제안요청서": 1}
            elif change == "truncated":
                rec["docs"][0]["text"] += "뒤쪽 문서 " * 4000
            else:
                f["qualification_complete"] = "no"
            out, _ = script.verify_company_size(f, rec, 16000)
            self.assertNotIn("v16", out)

    def test_schema_failure_is_not_unrestricted(self):
        obj = {"company_size": facts()}
        parsed, _ = script.parse_judgment(json.dumps(obj), script.COMPANY_SIZE_KEYS)
        self.assertEqual(parsed, obj)
        for key, value in [("qualification", "없음?"), ("qualification_complete", True),
                           ("priority_exception_quote", 42), ("scope_quote", "a" * 501)]:
            bad = copy.deepcopy(obj)
            bad["company_size"][key] = value
            with self.assertRaises(ValueError):
                script.parse_judgment(json.dumps(bad), script.COMPANY_SIZE_KEYS)
        del obj["company_size"]["qualification"]
        with self.assertRaises(ValueError):
            script.parse_judgment(json.dumps(obj), script.COMPANY_SIZE_KEYS)

    def test_vllm_uses_fact_schema_and_retries_once_without_mutating_baseline(self):
        runner = object.__new__(script.VLLMRunner)
        runner.sp = SimpleNamespace(max_tokens=2048, structured_outputs=SimpleNamespace(
            json=script.decode_schema(str(Path(__file__).resolve().parents[1] / "open/data"))))
        runner.count_tokens = lambda messages: 1000
        calls = []
        def chat(batch, sampling_params, **kwargs):
            schema = sampling_params.structured_outputs.json
            self.assertEqual(schema["required"], script.COMPANY_SIZE_KEYS)
            self.assertNotIn("위반여부", schema["properties"]["company_size"]["properties"])
            calls.append(schema)
            text = "{}" if len(calls) == 1 else json.dumps({"company_size": facts()})
            return [SimpleNamespace(outputs=[SimpleNamespace(text=text, token_ids=[1],
                                    finish_reason="stop", stop_reason=None)], prompt_token_ids=[1])]
        runner.llm = SimpleNamespace(chat=chat)
        messages = [{"role": "system", "content": script.COMPANY_SIZE_PROMPT},
                    {"role": "user", "content": "공고"}]
        text = script.run_chunk(runner, [messages], items=script.COMPANY_SIZE_KEYS, phase="company_size",
                                baseline_texts=[json.dumps(valid())])[0]
        self.assertEqual(json.loads(text)["company_size"], facts())
        self.assertEqual(len(calls), 2)
        self.assertEqual(runner.sp.structured_outputs.json["required"], script.ITEMS)

    def test_canary_refuses_mock_as_live_evidence(self):
        from tools.company_size_canary import measured
        with tempfile.TemporaryDirectory() as tmp:
            case = Path(tmp)
            (case / "run_report.json").write_text(json.dumps({"mode": "mock", "model_success_count": 0}),
                                                  encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "mock/api"):
                measured(case, [notice()], "irrelevant")

    def test_single_extra_stage_fallback_and_replay(self):
        from tools import replay_run
        calls = []

        class Runner(script.MockRunner):
            def chat(self, batch, items=None):
                calls.append(items)
                if items == script.COMPANY_SIZE_KEYS:
                    return [json.dumps({"company_size": facts()}) for _ in batch]
                base = valid()
                base["v1"] = {"위반여부": 1, "근거문구": "일반 의료기기 구매."}
                return [json.dumps(base) for _ in batch]

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "input.jsonl"
            recs = [notice(price) for price in (150_000_000, 50_000_000, 250_000_000)]
            for index, rec in enumerate(recs):
                rec["id"] += str(index)
            source.write_text("".join(json.dumps(rec, ensure_ascii=False) + "\n" for rec in recs), encoding="utf-8")
            out = root / "run/submission.csv"
            report = script.run(str(source), str(out), Runner, None, 128, 16000,
                                str(Path(__file__).resolve().parents[1] / "open/data"), debug_responses=True)
            self.assertEqual(calls, [None, script.COMPANY_SIZE_KEYS])
            self.assertEqual(report["reproduction"]["settings"]["extra_call_items"], script.extra_call_items())
            self.assertEqual(script.extra_call_items()["company_size"], script.BAND_ITEMS)
            self.assertEqual(report["company_size_selected_count"], 3)
            self.assertEqual(report["company_size_fallback_count"], 0)
            self.assertEqual(report["company_size_model_success_count"], 0)
            with out.open(encoding="utf-8") as stream:
                rows = list(csv.DictReader(stream))
            row = rows[0]
            self.assertEqual(row["v15"], "1")
            self.assertEqual(row["e15"], facts()["qualification_quote"])
            paired = out.with_name("company_size_baseline_submission.csv")
            with paired.open(encoding="utf-8") as stream:
                before_rows = list(csv.DictReader(stream))
            before = before_rows[0]
            changed = {k for k in row if row[k] != before[k]}
            self.assertEqual(changed, {"v15", "e15"})
            for before, after in zip(before_rows, rows):
                self.assertEqual(after["v1"], "1")
                for key in script.COLUMNS:
                    if key not in script.BAND_ITEMS + ["e" + v[1:] for v in script.BAND_ITEMS]:
                        self.assertEqual(before[key], after[key])
            self.assertEqual([row["v14"] for row in rows], ["0", "0", "1"])
            replay = replay_run.replay(script, out.parent, input_path=source,
                                      data_dir=Path(__file__).resolve().parents[1] / "open/data")
            self.assertEqual(replay_run.to_csv_bytes(script, replay["rows"]), out.read_bytes())

            # 진단 집계 검사만을 위한 합성 live 메타. 실제 모델 호출 증거로 보관하지 않는다.
            from tools.company_size_canary import measured
            synthetic = dict(report, mode="live", model_success_count=3, company_size_model_success_count=3)
            out.with_name("run_report.json").write_text(json.dumps(synthetic), encoding="utf-8")
            _, metrics = measured(out.parent, recs, script.records_sha256(recs))
            self.assertEqual(metrics["firings"], {"v14": 1, "v15": 1, "v16": 0, "v17": 0, "v18": 0})
            compressed = root / "input.jsonl.gz"
            with gzip.open(compressed, "wt", encoding="utf-8") as stream:
                stream.write(source.read_text(encoding="utf-8"))
            gz_recs = list(script.iter_records(str(compressed)))
            self.assertEqual(script.records_sha256(recs), script.records_sha256(gz_recs))
            self.assertNotEqual(script.records_sha256(recs), script.records_sha256(recs[::-1]))
            with self.assertRaisesRegex(ValueError, "입력/건수"):
                measured(out.parent, recs, "different-content")

            class Broken(Runner):
                def chat(self, batch, items=None):
                    return ["{}"] * len(batch) if items else super().chat(batch, items)
            failed = root / "failed/submission.csv"
            report = script.run(str(source), str(failed), Broken, None, 128, 16000,
                                str(Path(__file__).resolve().parents[1] / "open/data"))
            self.assertEqual(report["company_size_fallback_count"], 3)
            self.assertEqual(failed.read_bytes(), failed.with_name("company_size_baseline_submission.csv").read_bytes())


if __name__ == "__main__":
    unittest.main()
