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

    def test_raw_responses_only_attach_where_both_runs_agree(self):
        """dev-debug 는 별도 추론이다. 24칸이 다른 공고에 그 원응답을 붙이면 채점된 칸을
        열었을 때 다른 추론의 판정을 보게 된다 — 리뷰 라운드 1 P1."""
        base = ROOT / "reports/runs/colab-1789902969401579900"
        if not (base / "dev-debug/submission.csv").is_file():
            self.skipTest("dev-debug 가 있는 회차가 없다")
        entries = {
            path.relative_to(base).as_posix(): path.read_bytes()
            for part in ("dev", "dev-debug") for path in (base / part).glob("*")
        }
        report = build_report.build(self.score, "colab-0", entries, base)

        dev, _, _ = build_report.read_pred(self.score, entries["dev/submission.csv"])
        debug, _, _ = build_report.read_pred(self.score, entries["dev-debug/submission.csv"])
        differing = {i for i in dev if dev[i] != debug.get(i)}
        self.assertTrue(differing, "두 CSV 가 같으면 이 검사는 아무것도 안 지킨다")

        for identifier in differing:
            self.assertNotIn("raw", report["trace"].get(identifier, {}),
                             f"{identifier}: 24칸이 다른데 원응답이 붙었다")
        attached = {i for i, slot in report["trace"].items() if "raw" in slot}
        self.assertTrue(attached, "일치하는 공고에는 원응답이 붙어야 한다")
        self.assertFalse(attached & differing)
        self.assertIn(str(len(differing)), report["raw_note"])

    def test_dev_stats_are_not_overwritten_by_the_debug_run(self):
        """일치하는 공고라도 토큰 수·응답 길이는 그 추론의 것이다. dev 것을 덮으면 안 된다."""
        base = ROOT / "reports/runs/colab-1789902969401579900"
        if not (base / "dev-debug/diagnostics.jsonl").is_file():
            self.skipTest("dev-debug 가 있는 회차가 없다")
        entries = {
            path.relative_to(base).as_posix(): path.read_bytes()
            for part in ("dev", "dev-debug") for path in (base / part).glob("*")
        }
        report = build_report.build(self.score, "colab-0", entries, base)
        dev_only, _ = build_report.parse_diagnostics(entries["dev/diagnostics.jsonl"])
        for identifier, slot in report["trace"].items():
            if "responses" in slot:
                self.assertEqual(slot["responses"], dev_only[identifier]["responses"], identifier)

    def test_open_is_served_by_allowlist_not_by_path_check(self):
        """문자열 접두사 검사는 정션·심볼릭 링크의 실제 대상을 안 본다. `open/leak` 를 저장소
        밖으로 건 정션으로 밖의 파일이 실제로 새어 나왔다 — 리뷰 라운드 1 P0."""
        config = (ROOT / "web/vite.config.js").read_text(encoding="utf-8")
        self.assertIn("SERVED", config)
        self.assertIn("dev.jsonl", config)
        self.assertIn("dev_labels.csv", config)
        self.assertNotIn("startsWith(OPEN", config, "경로 접두사 검사로 되돌아갔다")
        self.assertNotIn("normalize(join(OPEN", config, "경로를 받아 정규화하는 방식으로 되돌아갔다")

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
