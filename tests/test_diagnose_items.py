"""항목 진단 도구를 모델 없이 검증한다. 제출물 script.py는 읽기만 한다."""

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("diagnose_items", ROOT / "tools/diagnose_items.py")
diagnose_items = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(diagnose_items)
SCRIPT = diagnose_items.load_submission_script()

ITEMS = ["v16", "v18", "v20"]
IDS = ["PPS-DEV-20", "PPS-DEV-22"]


def cell(stage, quote="공고 원문 한 줄"):
    return {"요구사항": "소기업 제한 없음 확인", "공고_인용": quote, "막힌_단계": stage}


class StubRunner:
    """모델 대신 정해진 응답을 돌려준다. 실제 판정이 아니다."""

    answers = None
    environment = {"runner": "stub"}

    def __init__(self, schema, **_):
        self.items = list(schema["properties"])
        self.schema = schema
        self.last_response_info = []
        StubRunner.seen_schema = schema

    def count_tokens(self, messages):
        return sum(len(message["content"]) for message in messages) // 2

    def chat(self, batch, sampling_params=None, items=None):
        self.last_response_info = [{"prompt_tokens": 100, "finish_reason": "stop"} for _ in batch]
        answers = StubRunner.answers or [{item: cell(diagnose_items.STAGES[1]) for item in self.items}]
        return [json.dumps(answers[i % len(answers)], ensure_ascii=False) for i in range(len(batch))]


def run(output_dir, **kwargs):
    return diagnose_items.diagnose(
        SCRIPT, kwargs.pop("items", ITEMS), kwargs.pop("ids", IDS),
        input_path=ROOT / "open/dev.jsonl", data_dir=ROOT / "open/data",
        output_dir=output_dir, runner_cls=kwargs.pop("runner_cls", StubRunner), **kwargs)


class DiagnoseItemsTests(unittest.TestCase):
    def setUp(self):
        StubRunner.answers = None

    def test_writes_one_row_per_notice_with_stage_counts_and_truth(self):
        StubRunner.answers = [
            {item: cell("condition_not_met") for item in ITEMS},
            {item: cell("context_not_observed", quote=None) for item in ITEMS},
        ]
        script_before = (ROOT / "script.py").read_bytes()
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "run"
            manifest = run(out, labels_path=ROOT / "open/dev_labels.csv")
            rows = [json.loads(line) for line in (out / "items.jsonl").read_text(encoding="utf-8").splitlines()]
            self.assertEqual([row["id"] for row in rows], IDS)
            self.assertEqual(sorted(rows[0]["items"]), sorted(ITEMS))
            self.assertEqual(rows[0]["items"]["v16"]["막힌_단계"], "condition_not_met")
            # 위반 여부는 모델이 아니라 프로그램이 단계에서 정한다. 둘이 어긋날 수 없다.
            self.assertEqual(rows[0]["items"]["v16"]["판정"], 0)
            self.assertEqual(rows[1]["items"]["v16"]["공고_인용"], None)
            # 실제 양성을 함께 실어야 "0이라 한 이유"와 정답을 한 줄에서 본다.
            self.assertEqual(rows[0]["truth"]["v16"], 1)
            self.assertEqual(rows[1]["truth"]["v18"], 1)
            self.assertEqual(manifest["stages"]["v16"],
                             {"context_not_observed": 1, "fact_not_extracted": 0,
                              "condition_not_met": 1, "violation_found": 0})
            self.assertEqual(manifest["purpose"], "item_diagnosis_only")
            self.assertEqual(manifest["notice_count"], 2)
            self.assertEqual(sorted(p.name for p in out.iterdir()), ["items.jsonl", "manifest.json"])
        self.assertEqual((ROOT / "script.py").read_bytes(), script_before, "제출물을 건드렸다")

    def test_verdict_is_derived_from_the_stage_never_from_a_separate_field(self):
        """판정을 별도 칸으로 두었더니 370건 중 286건이 단계와 어긋났다. 이제 한 칸이다."""
        self.assertNotIn("판정", diagnose_items.CELL)
        self.assertNotIn("판정", diagnose_items.build_schema(ITEMS)["properties"]["v16"]["properties"])
        StubRunner.answers = [{item: cell(diagnose_items.VIOLATION) for item in ITEMS}]
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "run"
            run(out)
            rows = [json.loads(line) for line
                    in (out / "items.jsonl").read_text(encoding="utf-8").splitlines()]
            self.assertTrue(all(r["items"][i]["판정"] == 1 for r in rows for i in ITEMS))

    def test_absence_items_are_asked_for_a_quotation(self):
        """부재탐지 항목은 제출 스키마가 근거를 null로 막는다. 진단 스키마는 막지 않아야 한다."""
        schema = diagnose_items.build_schema(ITEMS)
        for item in ITEMS:
            self.assertIn(item, SCRIPT.ABSENCE)
            self.assertEqual(schema["properties"][item]["properties"]["공고_인용"]["type"],
                             ["string", "null"])
        prompt = diagnose_items.build_prompt(SCRIPT.item_table(str(ROOT / "open/data")), ITEMS)
        for stage in diagnose_items.STAGES:
            self.assertIn(stage, prompt)
        self.assertIn("부재탐지", prompt)
        self.assertIn("not a submission judgment", prompt)

    def test_refuses_bad_inputs_without_writing_anything(self):
        cases = {
            "이미 있다": dict(existing=True),
            "항목표에 없는": dict(items=["v16", "v99"]),
            "입력에 없는 공고 ID": dict(ids=["PPS-DEV-20", "PPS-NOPE-1"]),
        }
        for message, kwargs in cases.items():
            with self.subTest(message), tempfile.TemporaryDirectory() as tmp:
                out = Path(tmp) / "run"
                if kwargs.pop("existing", False):
                    out.mkdir()
                with self.assertRaisesRegex(ValueError, message):
                    run(out, **kwargs)
                self.assertEqual(list(out.iterdir()) if out.exists() else [], [])
        with tempfile.TemporaryDirectory() as tmp:
            empty = Path(tmp) / "empty.jsonl"
            empty.write_text("", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "진단할 공고가 없다"):
                diagnose_items.diagnose(SCRIPT, ITEMS, [], input_path=empty,
                                        data_dir=ROOT / "open/data", output_dir=Path(tmp) / "run",
                                        runner_cls=StubRunner)

    def test_rejects_a_malformed_model_answer(self):
        broken = {
            "항목 키 불일치": {"v16": cell("condition_not_met")},
            "필드 불일치": {item: {"판정": 0} for item in ITEMS},
            "규약 밖이다": {item: {**cell("condition_not_met"), "막힌_단계": "gave_up"} for item in ITEMS},
        }
        for message, answer in broken.items():
            with self.subTest(message), tempfile.TemporaryDirectory() as tmp:
                StubRunner.answers = [answer]
                out = Path(tmp) / "run"
                with self.assertRaisesRegex(ValueError, message):
                    run(out)
                self.assertFalse(out.exists())

    def test_cli_mock_run_and_failure_exit_code(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "run"
            argv = ["--items", ",".join(ITEMS), "--ids", ",".join(IDS),
                    "--input", str(ROOT / "open/dev.jsonl"), "--data-dir", str(ROOT / "open/data"),
                    "--output-dir", str(out), "--mock"]
            self.assertEqual(diagnose_items.main(argv), 0)
            self.assertEqual(json.loads((out / "manifest.json").read_text(encoding="utf-8"))["runner"],
                             "MockRunner")
            self.assertEqual(diagnose_items.main(argv), 1, "기존 출력 폴더를 덮어썼다")


if __name__ == "__main__":
    unittest.main()
