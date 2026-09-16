"""로컬 채점 수치·입력 경계·공식 dev를 모델 없이 검증한다."""

import csv
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools/score.py"
HEADER = ["id"] + [f"v{i}" for i in range(1, 25)] + [f"e{i}" for i in range(1, 25)]


def row(identifier, positives=()):
    return [identifier] + [str(int(i in positives)) for i in range(1, 25)] + [""] * 24


def csv_bytes(rows):
    stream = io.StringIO(newline="")
    csv.writer(stream, lineterminator="\n").writerows(rows)
    return stream.getvalue().encode("utf-8")


class ScoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="t2 한글 ")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.truth = self.root / "truth.csv"
        self.pred = self.root / "pred.csv"
        self.output = self.root / "result"

    def run_cli(self, output=None):
        return subprocess.run(
            [sys.executable, "-X", "utf8", str(SCRIPT), "--truth", str(self.truth),
             "--pred", str(self.pred), "--output-dir", str(output or self.output)],
            cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=20,
        )

    def write_pair(self, truth, pred):
        self.truth.write_bytes(csv_bytes([HEADER] + truth))
        self.pred.write_bytes(csv_bytes([HEADER] + pred))

    def read_result(self, output=None):
        output = output or self.output
        for name in ("metrics.json", "errors.csv", "manifest.json", "result.md"):
            raw = (output / name).read_bytes()
            self.assertFalse(raw.startswith(b"\xef\xbb\xbf"))
            self.assertNotIn(b"\r", raw)
            raw.decode("utf-8")
        metrics = json.loads((output / "metrics.json").read_text(encoding="utf-8"))
        manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["status"], "draft")
        self.assertEqual(manifest["execution_status"], "complete")
        for key in ("model", "prompt_hash", "reviewer", "reviewed_at", "decision"):
            self.assertIsNone(manifest[key])
        self.assertEqual(manifest["generator"]["sha256"], hashlib.sha256(SCRIPT.read_bytes()).hexdigest())
        for source in manifest["sources"]:
            self.assertEqual(source["sha256"], hashlib.sha256(Path(source["path"]).read_bytes()).hexdigest())
        with (output / "errors.csv").open(encoding="utf-8", newline="") as f:
            errors = list(csv.DictReader(f))
        return metrics, errors

    def test_hand_calculation_and_order(self):
        truth = [row("z", (1, 2)), row("a", (1,)), row("m", (1,)), row("n")]
        pred = [row("z", (1,)), row("a", (1, 2)), row("m", (3,)), row("n", (1,))]
        self.write_pair(truth, pred)
        result = self.run_cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        metrics, errors = self.read_result()
        self.assertEqual(metrics["items"]["v1"], {
            "tp": 2, "fp": 1, "fn": 1, "precision": 2 / 3,
            "recall": 2 / 3, "f1": 2 / 3, "support": 3,
        })
        self.assertEqual(metrics["items"]["v2"]["fp"], 1)
        self.assertEqual(metrics["items"]["v2"]["fn"], 1)
        self.assertEqual(metrics["items"]["v3"]["precision"], 0)
        self.assertEqual(metrics["items"]["v3"]["recall"], 0)
        self.assertTrue(all(value == 0 for value in metrics["items"]["v24"].values()))
        self.assertAlmostEqual(metrics["macro_f1"], (2 / 3) / 24)
        self.assertEqual([(e["id"], e["item"]) for e in errors],
                         [("a", "v2"), ("m", "v1"), ("m", "v3"), ("n", "v1"), ("z", "v2")])
        for error in errors:
            self.assertEqual([error[k] for k in ("cause", "evidence_location", "owner", "note")],
                             ["", "", "", "미분류"])
        self.write_pair(list(reversed(truth)), list(reversed(pred)))
        shuffled = self.root / "shuffled"
        self.assertEqual(self.run_cli(shuffled).returncode, 0)
        self.assertEqual(self.read_result(shuffled), (metrics, errors))
        # RFC quoting and evidence text do not change label scores.
        pred[0][25] = '근거, "인용"\n다음 줄'
        self.write_pair(truth, pred)
        self.pred.write_bytes(self.pred.read_bytes().replace(b",1,", b',"1",'))
        quoted = self.root / "quoted"
        self.assertEqual(self.run_cli(quoted).returncode, 0)
        self.assertEqual(self.read_result(quoted), (metrics, errors))

    def test_invalid_inputs_on_both_sides(self):
        good = csv_bytes([HEADER, row("a")])
        invalid = {
            "empty": b"", "header_only": csv_bytes([HEADER]),
            "blank_id": csv_bytes([HEADER, row("")]),
            "whitespace_id": csv_bytes([HEADER, row(" \t")]),
            "duplicate": csv_bytes([HEADER, row("a"), row("a")]),
            "extra_id": csv_bytes([HEADER, row("a"), row("b")]),
            "wrong_id": csv_bytes([HEADER, row("b")]),
            "id_not_trimmed": csv_bytes([HEADER, row(" a")]),
            "header_order": csv_bytes([list(reversed(HEADER)), row("a")]),
            "header_duplicate": csv_bytes([["id"] + ["v1"] * 48, row("a")]),
            "short_row": csv_bytes([HEADER, row("a")[:-1]]),
            "long_row": csv_bytes([HEADER, row("a") + [""]]),
            "blank_row": good + b"\n", "bom": b"\xef\xbb\xbf" + good,
            "invalid_utf8": good + b"\xff",
            "bad_quote": csv_bytes([HEADER]) + b'"unterminated',
        }
        for value in ("", "True", "False", "0.5", "1.0", "2", "-1", " 1", "1 "):
            bad = row("a")
            bad[1] = value
            invalid[f"v={value!r}"] = csv_bytes([HEADER, bad])
        for name, item, value in (("zero_e", 1, "근거"), ("absence_e", 10, "근거"),
                                  ("long_e", 2, "가" * 501), ("formula_e", 2, "=1"),
                                  ("non_nfc", 2, "가")):
            bad = row("a", (2, 10))
            bad[24 + item] = value
            invalid[name] = csv_bytes([HEADER, bad])
        for side in (self.truth, self.pred):
            for name, raw in invalid.items():
                with self.subTest(side=side.name, case=name):
                    self.truth.write_bytes(good)
                    self.pred.write_bytes(good)
                    side.write_bytes(raw)
                    result = self.run_cli()
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn("error:", result.stderr)
                    self.assertEqual(result.stdout, "")
                    self.assertFalse(self.output.exists())
                    self.assertEqual(side.read_bytes(), raw)

    def test_output_and_input_protection(self):
        self.write_pair([row("a")], [row("a")])
        self.assertEqual(self.run_cli().returncode, 0)
        saved = {p.name: p.read_bytes() for p in self.output.iterdir()}
        repeated = self.run_cli()
        self.assertNotEqual(repeated.returncode, 0)
        self.assertEqual(repeated.stdout, "")
        self.assertEqual(saved, {p.name: p.read_bytes() for p in self.output.iterdir()})
        original = self.truth.read_bytes()
        self.assertNotEqual(self.run_cli(self.truth).returncode, 0)
        self.assertEqual(self.truth.read_bytes(), original)
        self.assertNotEqual(self.run_cli(self.root).returncode, 0)
        self.assertNotEqual(self.run_cli(self.truth / "cannot-write").returncode, 0)
        self.assertEqual(self.truth.read_bytes(), original)
        self.pred.unlink()
        self.assertNotEqual(self.run_cli(self.root / "missing").returncode, 0)
        self.assertFalse((self.root / "missing").exists())

    def test_official_dev(self):
        self.truth = ROOT / "open/dev_labels.csv"
        original = self.truth.read_bytes()
        self.pred.write_bytes(original)
        self.assertEqual(self.run_cli().returncode, 0)
        metrics, errors = self.read_result()
        self.assertEqual(metrics["macro_f1"], 1)
        self.assertEqual(metrics["truth_count"], 200)
        self.assertEqual(metrics["pred_count"], 200)
        self.assertTrue(metrics["ids_match"])
        self.assertTrue(all(m["f1"] == 1 for m in metrics["items"].values()))
        self.assertEqual(errors, [])
        with self.truth.open(encoding="utf-8", newline="") as f:
            records = list(csv.reader(f))[1:]
        self.pred.write_bytes(csv_bytes([HEADER] + [row(r[0]) for r in records]))
        zero_dir = self.root / "zero"
        self.assertEqual(self.run_cli(zero_dir).returncode, 0)
        zero, errors = self.read_result(zero_dir)
        self.assertEqual(zero["macro_f1"], 0)
        self.assertEqual(len(errors), sum(int(v) for r in records for v in r[1:25]))
        self.assertTrue(all((e["true"], e["pred"]) == ("1", "0") for e in errors))
        self.pred.write_bytes(csv_bytes([HEADER] + [row(r[0]) for r in reversed(records)]))
        shuffled_dir = self.root / "zero-shuffled"
        self.assertEqual(self.run_cli(shuffled_dir).returncode, 0)
        self.assertEqual(self.read_result(shuffled_dir), (zero, errors))
        self.assertEqual(self.truth.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
