"""A1 결정표·실패 보존·한 번 추출·재생 계약. 모델 성능 검사가 아니다."""

import copy
import csv
import gzip
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

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
    return dict(script.empty_company_size(), scope="general", scope_quote="일반 의료기기 구매.",
                qualification_role="none" if qualification == "unrestricted" else "eligibility",
                qualification=qualification, qualification_quote=quotes[qualification],
                qualification_complete="yes", priority_exception="no", priority_exception_quote=None,
                size_exception="none", size_exception_quote=None)


class CompanySizeTests(unittest.TestCase):
    def test_v13_needs_a_quote_the_notice_actually_contains(self):
        """v13 근거문구는 모델이 준 문자열이 아니라 **공고에 있는** 인용이어야 한다.

        없이 세우면 지어낸 문구도, 프롬프트에 실린 법령 원문도 그대로 근거가 됐다.
        `company_size_products()`가 검증하지 않던 시절 dev 200건에서 근거가 공고에 없는
        v13 양성이 3셀 있었고, 분류·역할·인용이 함께 바뀌면 9 → 33셀로 열렸다.
        """
        rec = notice()
        rec["docs"][0]["text"] += " 세부품명번호 7811189902 직접생산확인증명서를 제출해야 한다."
        visible = script.build_context(rec)
        real = "소기업 또는 소상공인인 업체."
        self.assertIn(real, visible)
        base = dict(facts(), scope="competitive", scope_quote="일반 의료기기 구매.")
        with patch.object(script, "competitive_product", return_value=True):
            written, _ = script.verify_company_size(base, rec, 16000)
            self.assertEqual(written["v13"], {"위반여부": 1, "근거문구": real})
            for invented in ("이 문구는 공고에 없다", "「중소기업기본법」제2조의 중소기업", "", None):
                out, _ = script.verify_company_size(dict(base, qualification_quote=invented), rec, 16000)
                self.assertNotIn("v13", out, f"검증되지 않은 인용이 v13을 세웠다: {invented!r}")
            # v12의 근거는 모델 인용이 아니라 공고에서 뽑은 것이라 이 검증 밖이다.
            general, _ = script.verify_company_size(dict(base, scope="general"), rec, 16000)
            self.assertEqual(general["v12"]["위반여부"], 1)
            self.assertIn(general["v12"]["근거문구"], visible)

    def test_qualification_role_never_turns_a_checklist_into_a_restriction(self):
        rec = notice(50_000_000)
        rec["docs"][0]["text"] = (
            "일반 의료기기 구매. 입찰참가자격: 사업자등록 업체 누구나 참가 가능. "
            "제출서류: 중소기업확인서 1부.")
        f = dict(facts("unrestricted"), qualification_role="checklist")
        parsed, _ = script.parse_judgment(json.dumps({"company_size": f}), script.COMPANY_SIZE_KEYS)
        self.assertEqual(parsed["company_size"]["qualification_role"], "checklist")
        self.assertEqual(script.verify_company_size(f, rec, 16000)[0]["v18"]["위반여부"], 1)
        for role in ("eligibility", "unknown"):
            self.assertNotIn("v18", script.verify_company_size(dict(f, qualification_role=role), rec, 16000)[0])
        # 등급과 역할이 모순이면 보류한다. 체크리스트를 unrestricted로 강제 변환하지 않는다.
        f.update(qualification="sme_allowed", qualification_quote="중소기업확인서 1부.")
        out, _ = script.verify_company_size(f, rec, 16000)
        self.assertFalse(set(out) & {"v17", "v18"})
        independent = dict(f, scope="competitive", requirements_complete="yes", software_business="yes",
                           software_business_quote="일반 의료기기 구매.")
        out, _ = script.verify_company_size(independent, rec, 16000)
        self.assertEqual([out[v]["위반여부"] for v in ("v10", "v20")], [1, 1])
        # 옛 스키마는 역할을 추측하지 않고 그대로 재생한다. 새 응답은 필드가 필수다.
        del f["qualification_role"]
        with self.assertRaisesRegex(ValueError, "필드 결손"):
            script.parse_judgment(json.dumps({"company_size": f}), script.COMPANY_SIZE_KEYS)
        old, _ = script.parse_judgment(json.dumps({"company_size": f}), script.COMPANY_SIZE_KEYS,
                                      company_size_qualification_role=False)
        self.assertEqual(script.verify_company_size(old["company_size"], rec, 16000)[0]["v17"]["위반여부"], 1)

    def test_clause_quotes_separate_observation_from_applicability(self):
        rec, f = notice(50_000_000), facts("unrestricted")
        rec["docs"][0]["text"] = "정보시스템 개발 용역. 사업자등록 업체 누구나 참가 가능."
        # `v20_decision()` (#111) decides v20 from the notice: it needs the 1468 registration.
        rec["meta"]["면허업종제한목록"] = "소프트웨어사업자(컴퓨터관련서비스사업)(1468)"
        f.update(scope="competitive", scope_quote="정보시스템 개발 용역.", requirements_complete="yes",
                 direct_production_quote=None, software_business="yes",
                 software_business_quote="정보시스템 개발 용역.", software_participation_quote=None)
        for field in ("direct_production", "software_participation"):
            f.pop(field, None)
        out, _ = script.verify_company_size(f, rec, 16000)
        self.assertEqual([out.get(v, {}).get("위반여부") for v in ("v10", "v20")], [1, 1])
        # 옛 unknown/not_required를 새 부재 관측으로 바꾸면 과거 회차를 조작하게 된다.
        old = dict(f, direct_production="not_required", software_participation="unknown")
        out, _ = script.verify_company_size(old, rec, 16000)
        self.assertFalse(set(out) & {"v10", "v20"})
        obj = {"company_size": f}
        parsed, _ = script.parse_judgment(json.dumps(obj), script.COMPANY_SIZE_KEYS)
        self.assertEqual(parsed, obj)
        self.assertFalse({"direct_production", "software_participation"}
                         & script.company_size_schema()["properties"].keys())
        long_quote = {"company_size": dict(f, software_business_quote="a" * 121)}
        with self.assertRaisesRegex(ValueError, "software_business_quote"):
            script.parse_judgment(json.dumps(long_quote), script.COMPANY_SIZE_KEYS)
        archived = {"company_size": dict(long_quote["company_size"], direct_production="not_required",
                                        software_participation="unknown")}
        archived_parsed, _ = script.parse_judgment(json.dumps(archived), script.COMPANY_SIZE_KEYS,
                                                  company_size_clause_quotes=False)
        self.assertEqual(archived_parsed, archived)

        from tools import replay_run
        class QuotesRunner(script.MockRunner):
            def chat(self, batch, items=None):
                if items == script.COMPANY_SIZE_KEYS:
                    return [json.dumps({"company_size": f}) for _ in batch]
                return super().chat(batch, items)
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "input.jsonl"
            source.write_text(json.dumps(rec, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
            output = Path(tmp) / "run/submission.csv"
            data = Path(__file__).resolve().parents[1] / "open/data"
            report = script.run(str(source), str(output), QuotesRunner, None, 128, 16000, str(data),
                                debug_responses=True)
            self.assertTrue(report["reproduction"]["settings"]["company_size_clause_quotes"])
            self.assertTrue(report["reproduction"]["settings"]["company_size_qualification_role"])
            replayed = replay_run.replay(script, output.parent, input_path=source, data_dir=data)
            self.assertEqual(replay_run.to_csv_bytes(script, replayed["rows"]), output.read_bytes())
            self.assertEqual([replayed["rows"][0][v] for v in ("v10", "v20")], [1, 1])
        del obj["company_size"]["software_participation_quote"]
        with self.assertRaisesRegex(ValueError, "필드 결손"):
            script.parse_judgment(json.dumps(obj), script.COMPANY_SIZE_KEYS)

    def test_document_absence_reaches_csv_without_inventing_unseen_facts(self):
        rec = notice(50_000_000)
        rec["docs"][0]["text"] = (
            "정보시스템 개발 용역. 입찰참가자격: 사업자등록 업체 누구나 참가 가능.")
        # `v20_decision()` (#111) decides v20 from the notice: it needs the 1468 registration.
        rec["meta"]["면허업종제한목록"] = "소프트웨어사업자(컴퓨터관련서비스사업)(1468)"
        f = facts("unrestricted")
        f.update(scope="competitive", scope_quote="정보시스템 개발 용역.",
                 requirements_complete="yes", direct_production="absent", direct_production_quote=None,
                 software_business="yes", software_business_quote="정보시스템 개발 용역.",
                 software_participation="absent", software_participation_quote=None)
        out, _ = script.verify_company_size(f, rec, 16000)
        self.assertEqual([v for v in ("v10", "v20") if out.get(v, {}).get("위반여부") == 1],
                         ["v10", "v20"])
        row = script.to_row(rec["id"], script.postprocess({**valid(), **out}, rec))
        self.assertEqual([row[v] for v in ("v10", "v20")], [1, 1])
        self.assertFalse(row["e10"] or row["e20"])
        # SW 명시 장소인 공고문/RFP는 완전 관측, 규격서만 잘리면 SW 부재는 관측 가능하다.
        spec_tail = copy.deepcopy(rec)
        spec_tail["docs"].append({"doc_id": "b", "type": "규격서", "text": "장비 규격 " * 5000})
        partial, _ = script.verify_company_size(f, spec_tail, 16000)
        self.assertEqual(partial["v20"]["위반여부"], 1)
        self.assertNotIn("v10", partial)
        spec_tail["docs"][-1]["type"] = "제안요청서"
        self.assertNotIn("v20", script.verify_company_size(f, spec_tail, 16000)[0])
        # 미관측·메타에만 있는 인용으로는 부재를 확정하지 않는다.
        for change in ("missing", "truncated", "unobserved", "unknown", "metadata_quote"):
            candidate, record = copy.deepcopy(f), copy.deepcopy(rec)
            if change == "missing":
                record["input_completeness"]["완전관측"] = False
            elif change == "truncated":
                record["docs"][0]["text"] += "뒤쪽 문서 " * 4000
            elif change == "unobserved":
                candidate["requirements_complete"] = "no"
            elif change == "unknown":
                candidate.update(direct_production="unknown", software_participation="unknown")
            else:
                record["meta"]["조항호내용"] = "본문에 없는 적용 대상"
                candidate.update(scope_quote="본문에 없는 적용 대상",
                                 software_business_quote="본문에 없는 적용 대상")
            with self.subTest(change=change):
                rejected, _ = script.verify_company_size(candidate, record, 16000)
                self.assertNotIn("v10", rejected)
                self.assertNotIn("v20", rejected)
        # 같은 사실 추출의 일반물품/무제한은 기존 결정표를 통해 v18에 닿는다.
        f.update(scope="general", software_business="no")
        out, _ = script.verify_company_size(f, rec, 16000)
        self.assertEqual(out["v18"], {"위반여부": 1, "근거문구": None})
        rec["docs"][0]["text"] += (
            " 직접생산확인증명서를 보유한 업체. 소프트웨어 진흥법 제48조에 따라 대기업 참여를 제한합니다.")
        f.update(scope="competitive", software_business="yes", direct_production="present",
                 direct_production_quote="직접생산확인증명서를 보유한 업체.",
                 software_participation="present",
                 software_participation_quote="소프트웨어 진흥법 제48조에 따라 대기업 참여를 제한합니다.")
        out, _ = script.verify_company_size(f, rec, 16000)
        self.assertEqual([out[v]["위반여부"] for v in ("v10", "v20")], [0, 0])

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
        old = {k: v for k, v in obj["company_size"].items()
               if k in script.company_size_schema(legacy=True)["properties"]}
        with self.assertRaisesRegex(ValueError, "필드 결손"):
            script.parse_judgment(json.dumps({"company_size": old}), script.COMPANY_SIZE_KEYS)
        replayed, _ = script.parse_judgment(json.dumps({"company_size": old}), script.COMPANY_SIZE_KEYS,
                                           company_size_legacy=True)
        self.assertEqual(replayed["company_size"], old)
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
                    assert all("메타에만 있는 소기업 제한" not in m[1]["content"] for m in batch)
                    return [json.dumps({"company_size": facts()}) for _ in batch]
                assert all("메타에만 있는 소기업 제한" in m[1]["content"] for m in batch)
                base = valid()
                base["v1"] = {"위반여부": 1, "근거문구": "일반 의료기기 구매."}
                return [json.dumps(base) for _ in batch]

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "input.jsonl"
            recs = [notice(price) for price in (150_000_000, 50_000_000, 250_000_000)]
            for index, rec in enumerate(recs):
                rec["id"] += str(index)
                rec["meta"]["조항호내용"] = "메타에만 있는 소기업 제한"
            source.write_text("".join(json.dumps(rec, ensure_ascii=False) + "\n" for rec in recs), encoding="utf-8")
            out = root / "run/submission.csv"
            report = script.run(str(source), str(out), Runner, None, 128, 16000,
                                str(Path(__file__).resolve().parents[1] / "open/data"), debug_responses=True)
            self.assertEqual(calls, [None, script.COMPANY_SIZE_KEYS])
            self.assertEqual(report["reproduction"]["settings"]["extra_call_items"], script.extra_call_items())
            # 이 단계가 덮어쓸 수 있는 열을 그대로 신고해야 노트북 보호 가드가 맞는 것을 지킨다.
            # 금액·등급 축(BAND_ITEMS)과 scope 축(SCOPE_ITEMS) 둘 다 이 한 호출에서 나온다.
            self.assertEqual(script.extra_call_items()["company_size"],
                             script.BAND_ITEMS + script.SCOPE_ITEMS + script.DOCUMENT_CHECK_ITEMS)
            self.assertFalse(set(script.BAND_ITEMS) & set(script.SCOPE_ITEMS))
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
            self.assertEqual(metrics["firings"], {v: int(v in ("v14", "v15"))
                                                 for v in script.extra_call_items()["company_size"]})
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
