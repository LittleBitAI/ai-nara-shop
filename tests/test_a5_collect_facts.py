"""CPU contract checks only; these do not claim successful GPU inference."""

import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from experiments import a5_collect_facts as a5


class FakeRunner:
    environment = {"test_only": True}
    load_seconds = 0

    def __init__(self, *args, **kwargs):
        self.calls = []
        self.fail = False

    def count_tokens(self, messages):
        assert "DO_NOT_COPY_REGISTERED_VALUE" not in str(messages)
        assert messages[0]["content"] == a5.script.COMPANY_SIZE_PROMPT
        return 100

    def chat(self, batch, items):
        assert items == a5.script.COMPANY_SIZE_KEYS
        self.calls.append(len(batch))
        response = "invalid" if self.fail else json.dumps({"company_size": a5.script.empty_company_size()})
        return [response] * len(batch)


def records(prefix, count):
    return [dict(id=f"{prefix}-{i}", meta={"조항호내용": "DO_NOT_COPY_REGISTERED_VALUE"},
                 docs=[dict(doc_id="D0", type="공고문", text="물품 구매 공고")],
                 input_completeness={"완전관측": True}, dropped_doc_counts={}) for i in range(count)]


class A5FactsTests(unittest.TestCase):
    def test_resume_and_failed_shard_preserve_completed_observations(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            model = root / a5.script.MODEL_REVISION
            model.mkdir()
            source, output = root / "unlabeled.jsonl", root / "results"
            source.write_text("synthetic test data\n", encoding="utf-8")
            runner = FakeRunner()
            real_hash = a5.file_hash
            argv = ["a5", "--input", str(source), "--output-dir", str(output), "--model-dir", str(model)]
            with patch.object(sys, "argv", argv), \
                    patch.object(a5, "file_hash", side_effect=lambda p: a5.UNLABELED_SHA256 if Path(p) == source else real_hash(p)), \
                    patch.object(a5.script, "iter_records", side_effect=lambda p: iter(records("dev", 200) if Path(p).name == "dev.jsonl" else records("unlabeled", 20000))), \
                    patch.object(a5.script, "VLLMRunner", return_value=runner):
                a5.main()
                self.assertEqual(sum(runner.calls), 1200)
                first_bytes = (output / "unlabeled-00.json").read_bytes()
                a5.main()
                self.assertEqual(sum(runner.calls), 2200)
                self.assertEqual((output / "unlabeled-00.json").read_bytes(), first_bytes)
                summary = json.loads((output / "summary.json").read_text())
                self.assertEqual(summary["unlabeled"]["count"], 2000)
                self.assertIsNone(summary["unlabeled_over_dev_rate"])
                self.assertFalse(summary["complete"])
                runner.fail = True
                with self.assertRaises(RuntimeError):
                    a5.main()
                self.assertFalse((output / "unlabeled-02.json").exists())
                self.assertEqual((output / "unlabeled-00.json").read_bytes(), first_bytes)
                self.assertEqual(json.loads((output / "summary.json").read_text())["unlabeled"]["count"], 2000)
                damaged = json.loads(first_bytes)
                damaged["payload"]["rows"][0]["h2_fired"] = True
                a5.save(output / "unlabeled-00.json", damaged)
                with self.assertRaisesRegex(ValueError, "contract/content mismatch"):
                    a5.main()

    def test_rate_uses_covered_rows_and_does_not_call_partial_data_complete(self):
        completed = {"dev": {"payload": {"rows": [{"h2_fired": i < 3} for i in range(200)]}},
                     "unlabeled-00": {"payload": {"rows": [{"h2_fired": i < 12} for i in range(1000)]}}}
        result = a5.summarize(completed)
        self.assertAlmostEqual(result["unlabeled_over_dev_rate"], 0.8)
        self.assertFalse(result["complete"])


if __name__ == "__main__":
    unittest.main()
