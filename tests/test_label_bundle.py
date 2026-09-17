"""라벨 번들 도구를 외부 모델 없이 검증한다. 제출물 script.py는 읽기만 한다."""

import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def _load(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


label_bundle = _load("label_bundle", "tools/label_bundle.py")
score = _load("score", "tools/score.py")
SCRIPT = label_bundle.load_submission_script()
IDS = ["PPS-DEV-01", "PPS-DEV-02"]

# stdin으로 받은 프롬프트를 버리고 정해진 JSON만 낸다. 실제 라벨이 아니다.
STUB = (
    f"{sys.executable} -X utf8 -c \""
    "import sys,json;sys.stdin.read();"
    "print(json.dumps({'v%d'%i:{'위반여부':0,'근거문구':None,'정보부족':False} for i in range(1,25)},"
    "ensure_ascii=False))\""
)


def reply(**overrides):
    cells = {item: {"위반여부": 0, "근거문구": None, "정보부족": False} for item in label_bundle.ITEMS}
    cells.update(overrides)
    return json.dumps(cells, ensure_ascii=False)


class ExportTest(unittest.TestCase):
    def test_refuses_a_bundle_inside_the_repository(self):
        """dev 정답과 과거 오답 분석이 같은 트리에 있으면 블라인드 비교가 깨진다."""
        with self.assertRaises(ValueError) as caught:
            label_bundle.export(SCRIPT, input_path=ROOT / "open/dev.jsonl",
                                data_dir=ROOT / "open/data", bundle=ROOT / "artifacts/bundle")
        self.assertIn("저장소 안에 만들 수 없다", str(caught.exception))

    def test_bundle_carries_the_notices_and_the_law_but_no_answers(self):
        with tempfile.TemporaryDirectory() as temporary:
            bundle = Path(temporary) / "compare"
            manifest = label_bundle.export(SCRIPT, input_path=ROOT / "open/dev.jsonl",
                                           data_dir=ROOT / "open/data", bundle=bundle, ids=IDS)
            self.assertEqual(manifest["notice_count"], len(IDS))
            self.assertEqual([n["id"] for n in manifest["notices"]], IDS)
            self.assertTrue((bundle / "prompt.md").is_file())
            self.assertTrue((bundle / "법령패키지/법령").is_dir())
            self.assertGreater(manifest["law_file_count"], 20)
            self.assertFalse((bundle / f"{bundle.name}.partial").exists())

            names = {p.name for p in bundle.rglob("*") if p.is_file()}
            self.assertNotIn("dev_labels.csv", names)
            self.assertNotIn("cases.jsonl", names)

            prompt = (bundle / "prompt.md").read_text(encoding="utf-8")
            self.assertEqual(label_bundle.digest(prompt), manifest["prompt_sha256"])
            for item in label_bundle.ITEMS:
                self.assertIn(f"- {item}: ", prompt)
            self.assertIn("[부재탐지", prompt)           # 5개 부재탐지 항목이 표시된다
            self.assertIn("Do not search the web", prompt)  # R6

            notice = (bundle / "notices/PPS-DEV-01.md").read_text(encoding="utf-8")
            self.assertIn("## 나라장터 등록 정보", notice)
            self.assertIn("input_completeness", notice)
            self.assertEqual(label_bundle.digest(notice), manifest["notices"][0]["sha256"])

    def test_rejects_an_unknown_notice_id(self):
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaises(ValueError) as caught:
                label_bundle.export(SCRIPT, input_path=ROOT / "open/dev.jsonl",
                                    data_dir=ROOT / "open/data",
                                    bundle=Path(temporary) / "b", ids=["PPS-DEV-01", "없는ID"])
            self.assertIn("없는ID", str(caught.exception))


class ParseTest(unittest.TestCase):
    def test_marks_a_quotation_that_is_not_in_the_notice(self):
        """틀린 인용으로 공고 전체를 버리지 않는다. 근거 정확성은 모델 비교 축이라 표시만 한다."""
        notice = "공고 원문에 실제로 있는 문장이다."
        parsed = label_bundle.parse_labels(
            SCRIPT, reply(v3={"위반여부": 1, "근거문구": "실제로 있는 문장", "정보부족": False},
                          v5={"위반여부": 1, "근거문구": "지어낸 문장", "정보부족": False}),
            "PPS-DEV-01", notice)
        self.assertTrue(parsed["v3"]["인용_원문일치"])
        self.assertFalse(parsed["v5"]["인용_원문일치"])
        self.assertFalse(parsed["v1"]["인용_길이초과"])

    def test_flags_an_overlong_quotation(self):
        quote = "가" * (label_bundle.EVIDENCE_MAX + 1)
        parsed = label_bundle.parse_labels(
            SCRIPT, reply(v9={"위반여부": 1, "근거문구": quote, "정보부족": False}),
            "PPS-DEV-01", quote)
        self.assertTrue(parsed["v9"]["인용_길이초과"])

    def test_names_the_encoding_when_the_reply_arrived_broken(self):
        """자식이 cp949로 내보내면 한국어 키가 깨진다. 엉뚱한 줄 대신 원인을 말해야 한다."""
        broken = reply().encode("cp949").decode("utf-8", "replace")
        with self.assertRaises(ValueError) as caught:
            label_bundle.parse_labels(SCRIPT, broken, "PPS-DEV-01", "본문")
        self.assertIn("stdout 인코딩이 UTF-8이 아니다", str(caught.exception))

    def test_rejects_broken_replies(self):
        cases = {
            "항목 키 불일치": json.dumps({"v1": {"위반여부": 0, "근거문구": None, "정보부족": False}}),
            "필드 불일치": reply(v2={"위반여부": 0, "근거문구": None}),
            "위반여부는 0 또는 1": reply(v4={"위반여부": True, "근거문구": None, "정보부족": False}),
            "정보부족은 true": reply(v6={"위반여부": 0, "근거문구": None, "정보부족": "no"}),
            "JSON 객체가 아니다": "판정을 내리지 못했습니다",
        }
        for expected, text in cases.items():
            with self.subTest(expected=expected):
                with self.assertRaises(ValueError) as caught:
                    label_bundle.parse_labels(SCRIPT, text, "PPS-DEV-01", "본문")
                self.assertIn(expected, str(caught.exception))


class RunAndCollectTest(unittest.TestCase):
    def test_labels_resume_and_produce_a_csv_the_scorer_accepts(self):
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            bundle = workspace / "compare"
            label_bundle.export(SCRIPT, input_path=ROOT / "open/dev.jsonl",
                                data_dir=ROOT / "open/data", bundle=bundle, ids=IDS)
            out = workspace / "labels/stub.jsonl"

            first = label_bundle.label(SCRIPT, bundle=bundle, cmd=STUB, out=out,
                                       model_label="stub", limit=1)
            self.assertEqual((first["requested"], first["labelled"], first["failures"]), (1, 1, []))

            second = label_bundle.label(SCRIPT, bundle=bundle, cmd=STUB, out=out, model_label="stub")
            self.assertEqual(second["skipped_already_done"], 1)  # 끝난 ID는 다시 부르지 않는다
            self.assertEqual(second["labelled"], 1)

            records = [json.loads(line) for line in out.read_text(encoding="utf-8").splitlines()]
            self.assertEqual([r["id"] for r in records], IDS)
            self.assertEqual({r["model"] for r in records}, {"stub"})
            self.assertTrue((bundle / "raw/stub/PPS-DEV-01.txt").is_file())
            self.assertTrue(out.with_name(out.name + ".manifest.json").is_file())

            predictions = workspace / "stub.csv"
            self.assertEqual(label_bundle.collect(labels=out, out=predictions)["rows"], len(IDS))
            loaded, _ = score.load_csv(predictions)  # 채점기의 49열 계약을 그대로 통과해야 한다
            self.assertEqual(sorted(loaded), sorted(IDS))
            self.assertEqual(loaded[IDS[0]], tuple([0] * 24))

    def test_a_failing_command_is_recorded_and_does_not_stop_the_run(self):
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            bundle = workspace / "compare"
            label_bundle.export(SCRIPT, input_path=ROOT / "open/dev.jsonl",
                                data_dir=ROOT / "open/data", bundle=bundle, ids=IDS)
            summary = label_bundle.label(
                SCRIPT, bundle=bundle, cmd=f"{sys.executable} -c \"import sys;sys.stdin.read();"
                                           "sys.exit(3)\"",
                out=workspace / "labels.jsonl", model_label="broken")
            self.assertEqual(summary["labelled"], 0)
            self.assertEqual(len(summary["failures"]), len(IDS))
            self.assertIn("3로 끝났다", summary["failures"][0]["error"])


if __name__ == "__main__":
    unittest.main()
