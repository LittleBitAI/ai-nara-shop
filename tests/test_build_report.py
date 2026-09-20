"""화면이 읽는 JSON이 tools/score.py의 채점과 같은지 검증한다. 모델 미사용."""

import argparse
import csv
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import build_report  # noqa: E402

HEADER = ["id"] + [f"v{i}" for i in range(1, 25)] + [f"e{i}" for i in range(1, 25)]


def csv_bytes(rows):
    stream = io.StringIO(newline="")
    csv.writer(stream, lineterminator="\n").writerows(rows)
    return stream.getvalue().encode("utf-8")


class BuildReportTests(unittest.TestCase):
    def setUp(self):
        self.score = build_report.load_score()
        self.truth, _ = self.score.load_csv(build_report.TRUTH)

    def test_matches_recorded_scoring(self):
        """등록된 회차의 항목 점수가 그 회차의 score/metrics.json과 한 자리도 다르지 않다.

        채점기를 화면 쪽에 다시 짜지 않았다는 것이 여기서만 확인된다.
        """
        checked = 0
        for recorded in sorted((ROOT / "reports/runs").glob("*/score/metrics.json")):
            run_id = recorded.parent.parent.name
            entries = {
                path.relative_to(recorded.parent.parent).as_posix(): path.read_bytes()
                for path in (recorded.parent.parent / "dev").glob("*")
            }
            report = build_report.build(self.score, run_id, entries, recorded.parent.parent)
            reference = json.loads(recorded.read_text(encoding="utf-8"))
            self.assertEqual(report["macro_f1"], reference["macro_f1"], run_id)
            self.assertEqual(report["items"], reference["items"], run_id)
            checked += 1
        self.assertGreater(checked, 0, "대조할 회차가 없다")

    def test_grid_letters_agree_with_counts(self):
        """grid 한 칸의 글자가 tp/fp/fn 집계와 어긋나지 않는다."""
        path = next(iter(sorted((ROOT / "web/public/runs").glob("colab-*.json"))), None)
        if path is None:
            self.skipTest("build_report.py --all 을 먼저 돌린다")
        report = json.loads(path.read_text(encoding="utf-8"))
        for index, (name, metrics) in enumerate(report["items"].items()):
            column = [report["grid"][i][index] for i in report["ids"]]
            self.assertEqual(column.count(build_report.TP), metrics["tp"], name)
            self.assertEqual(column.count(build_report.FP), metrics["fp"], name)
            self.assertEqual(column.count(build_report.FN), metrics["fn"], name)

    def test_absence_items_carry_no_evidence(self):
        """부재탐지 5항목은 e가 항상 빈칸이라는 규약(D4-5)이 화면 입력에서도 지켜진다."""
        for path in sorted((ROOT / "web/public/runs").glob("colab-*.json")):
            report = json.loads(path.read_text(encoding="utf-8"))
            for identifier, quotes in report["evidence"].items():
                for name in quotes:
                    self.assertNotIn(int(name[1:]), build_report.ABSENCE,
                                     f"{path.name} {identifier} {name}")

    def test_latest_picks_the_newest_and_ignores_strangers(self):
        """--latest 가 이름 규약에 맞는 것 중 가장 최근을 고른다. 런처가 이름을 못 박지 않는다."""
        with tempfile.TemporaryDirectory(prefix=".inbox-") as temporary:
            inbox = Path(temporary)
            with self.assertRaises(ValueError):
                build_report.newest_zip(inbox)
            for name, stamp in (("colab-results-1.zip", 1_000_000),
                                ("colab-results-2.zip", 2_000_000),
                                ("colab-results-latest.zip", 3_000_000),
                                ("submit.zip", 4_000_000)):
                path = inbox / name
                path.write_bytes(b"")
                os.utime(path, (stamp, stamp))
            self.assertEqual(build_report.newest_zip(inbox).name, "colab-results-2.zip")

    def test_run_id_comes_from_the_name_not_a_guess(self):
        for name in ("results.zip", "colab-results-.zip", "colab-results-1789.tar.zip"):
            entries = {"dev/submission.csv": b""}
            args = argparse.Namespace(zip=Path(name), run=None)
            with self.assertRaises(ValueError, msg=name):
                build_report.read_source(args)

    def test_windows_launcher_is_ascii_and_crlf(self):
        """cmd.exe 는 배치 파일을 바이트 오프셋으로 되읽는다. 한글 + chcp 면 주석 조각이
        명령으로 실행되고, LF 뿐이면 블록이 어긋난다. 둘 다 실제로 낸 적 있는 고장이다."""
        raw = (ROOT / "report.cmd").read_bytes()
        self.assertEqual([b for b in raw if b > 127], [], "report.cmd 에 비ASCII 바이트가 있다")
        self.assertEqual(raw.count(b"\n") - raw.count(b"\r\n"), 0, "report.cmd 에 홀로 있는 LF 가 있다")

    def test_macos_launcher_is_lf_and_executable(self):
        raw = (ROOT / "report.command").read_bytes()
        self.assertEqual(raw.count(b"\r\n"), 0, "report.command 에 CRLF 가 섞이면 \\r 이 명령에 붙는다")
        self.assertTrue(raw.startswith(b"#!"), "shebang 이 없다")
        mode = subprocess.run(["git", "ls-files", "-s", "report.command"], cwd=ROOT,
                              capture_output=True, text=True).stdout
        self.assertTrue(mode.startswith("100755"), f"실행 비트가 없다: {mode.strip()!r}")

    def test_zip_slip_is_refused(self):
        for name in ("../escape.csv", "/abs.csv", "dev/../../out.csv"):
            with self.assertRaises(ValueError):
                build_report.safe_member(name)

    def test_zip_without_submission_is_refused(self):
        blob = io.BytesIO()
        with zipfile.ZipFile(blob, "w") as archive:
            archive.writestr("runtime.json", "{}")
        with zipfile.ZipFile(blob) as archive:
            entries = {i.filename: archive.read(i) for i in archive.infolist()}
        with self.assertRaises(ValueError):
            build_report.build(self.score, "colab-0", entries, ROOT)

    def test_broken_diagnostics_line_does_not_lose_the_run(self):
        blob = b'{"event": "run_started", "settings": {"seed": 1}}\n{ broken\n' \
               b'{"event": "sme_verified", "id": "PPS-DEV-01", "flags": {"v13": 0}}\n'
        per_id, settings = build_report.parse_diagnostics(blob)
        self.assertEqual(settings, {"seed": 1})
        self.assertEqual(per_id["PPS-DEV-01"]["sme"]["flags"], {"v13": 0})

    def test_evidence_quotes_survive_the_round_trip(self):
        """합성 예측으로 e열이 그대로 실리는지 본다. 채점기 검사이며 성능 검증이 아니다."""
        identifier = sorted(self.truth)[0]
        rows = [HEADER]
        for current in sorted(self.truth):
            values = ["1" if current == identifier else "0"] + ["0"] * 23
            quotes = ["인용" if current == identifier else ""] + [""] * 23
            rows.append([current] + values + quotes)
        entries = {"dev/submission.csv": csv_bytes(rows)}
        report = build_report.build(self.score, "colab-0", entries, ROOT)
        self.assertEqual(report["evidence"][identifier], {"v1": "인용"})
        self.assertEqual(len(report["evidence"]), 1)


if __name__ == "__main__":
    unittest.main()
