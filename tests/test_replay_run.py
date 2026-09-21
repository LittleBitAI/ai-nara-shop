"""보관된 원응답 재생을 검증한다. 모델을 부르지 않는다."""

import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("replay_run", ROOT / "tools/replay_run.py")
replay_run = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(replay_run)
SCRIPT = replay_run.load_module(ROOT / "script.py", "submission")
# **이 줄은 이 파일의 검사를 위한 것이 아니다.** 위 한 줄이 `sys.modules["submission"]` 에
# 두 번째 script 모듈을 **수집 시점에** 꽂는데, 후보들이 재생 대상 모듈을 그 이름으로 찾는다
# (`base = sys.modules.get("submission") or ... or script`). 카탈로그를 안 채운 채 꽂으면
# 그 후보가 품목 조회를 잃는다 — `a5_scope_pilot` 의 h2 갈래가 v13 TP 두 건을 잃고
# 13셀이 어긋났다. 단독 실행은 통과하고 전체 실행만 깨져 원인이 안 보인다.
# `replay_run.replay()` 는 언제나 이것을 부르므로, 이름을 꽂을 때 같은 상태로 맞춘다.
SCRIPT.load_sme_reference(str(ROOT / "open/data"))

# 원응답이 보관된 유일한 회차. 이 폴더가 없어지면 CPU 재평가 경로 전체가 근거를 잃는다.
CASE = ROOT / "reports/runs/colab-1789655036303880754/dev-debug"
PLAIN_CASE = ROOT / "reports/runs/colab-1789655036303880754/dev"
# 재현은 회차가 실제로 돌린 커밋의 코드로 확인한다. HEAD의 후처리는 바뀔 수 있다.
_SCRATCH = tempfile.TemporaryDirectory()
RUN_SCRIPT = replay_run.run_script(CASE, _SCRATCH.name)
# HEAD 코드로 같은 원응답을 재생한 고정 결과(PR #30, sha256 0818a23c…).
# 2026-09-20 재고정(sha256 beb68293…): 경쟁제품 규칙(v11·v12)이 postprocess에 들어왔다.
# 6셀만 움직였고 대상 밖 변화는 0이다 — v11 TP 0→2, v12 TP 0→2.
# 근거는 reports/team-c/a2-competitive-product/README.md.
# 2026-09-20 재고정(sha256 74dd4706…): v19가 인용이 아니라 공고의 요구를 보게 됐다.
# 14셀이 움직였고 대상 밖 변화는 0이다 — v19 오탐 15→3.
# 2026-09-20 재고정(sha256 8b154af0…): v21 하한이 계약법·공동도급 방식을 따른다.
# 6셀이 움직였고 대상 밖 변화는 0이다 — v21 오탐 10→4.
# 2026-09-20 재고정(sha256 3a0df088…): v5가 고시금액 미만 구간에서 발화하지 않는다.
# 5셀이 움직였고 대상 밖 변화는 0이다 — v5 오탐 6→1.
# 근거는 reports/team-b/b1-v19-bid-stage/README.md.
HEAD_REPLAY = ROOT / "reports/team-b/b5-port-replay/submission.csv"

CANDIDATE = '''"""검사용 후보. 모든 판정을 0으로 만든다."""


def postprocess(judgment, rec):
    return {item: {"위반여부": 0, "근거문구": ""} for item in judgment}
'''


class CsvCellDiffTests(unittest.TestCase):
    """보관 CSV 대신 셀 목록을 고정하려면 그 비교기가 구조 회귀를 놓치지 않아야 한다."""

    HEADER = "id,v1,e1\n"

    def test_reports_only_changed_cells_and_refuses_broken_structure(self):
        base = (self.HEADER + "A,0,\nB,1,근거\n").encode()
        self.assertEqual(replay_run.csv_cell_diff(base, base), [])
        changed = (self.HEADER + "A,1,\nB,1,다른 근거\n").encode()
        self.assertEqual(replay_run.csv_cell_diff(changed, base), [("A", "v1"), ("B", "e1")])
        # 행 순서는 ID 기반 채점이라 차이가 아니다.
        reordered = (self.HEADER + "B,1,근거\nA,0,\n").encode()
        self.assertEqual(replay_run.csv_cell_diff(reordered, base), [])
        # 구조가 깨지면 조용히 []를 돌려주지 않고 소리를 낸다.
        for data, message in [
            ((self.HEADER + "A,0,\nA,1,\n").encode(), "중복"),
            (("id,v1,e1,v2\n" + "A,0,,0\nB,1,근거,0\n").encode(), "열 구성"),
            ((self.HEADER + "A,0,\n").encode(), "id 집합"),
            # 헤더보다 길거나 짧은 행은 선언된 열만 순회하면 조용히 통과한다.
            ((self.HEADER + "A,0,,EXTRA\nB,1,근거\n").encode(), "길다"),
            ((self.HEADER + "A,0\nB,1,근거\n").encode(), "짧다"),
            # 양쪽이 똑같이 비어 있거나 뒤틀려도 [] 를 돌려주면 안 된다.
            (b"", "헤더가 없다"),
            (self.HEADER.encode(), "행이 없다"),
            (("v1,e1\n" + "0,\n").encode(), "첫 열이 id"),
            (("id,v1,v1\n" + "A,0,0\n").encode(), "중복 열"),
            ((self.HEADER + ",0,\nB,1,근거\n").encode(), "빈 id"),
        ]:
            with self.assertRaises(ValueError) as caught:
                replay_run.csv_cell_diff(data, base)
            self.assertIn(message, str(caught.exception))


class ReplayRunTests(unittest.TestCase):
    def test_loaded_script_is_reachable_as_sys_modules_submission(self):
        """후보가 이걸로 같은 제출 코드를 집는다. experiments/sme_candidate.baseline() 참고.

        main() 이 다시 돌면 새 모듈로 바뀌므로 모듈 수준 SCRIPT 와 견주지 않는다.
        """
        saved = sys.modules.get("submission")
        try:
            module = replay_run.load_module(ROOT / "script.py", "submission")
            self.assertIs(sys.modules.get("submission"), module)
        finally:
            if saved is None:
                sys.modules.pop("submission", None)
            else:
                sys.modules["submission"] = saved

    def test_failed_load_keeps_the_previous_registration(self):
        """--script 로 없는 경로를 받은 회차가 앞 회차의 제출 코드를 지우면 안 된다.

        main() 은 이 OSError 를 삼키고 1 을 돌려주므로, 지워지면 뒤이은
        sme_candidate.baseline() 이 조용히 워킹트리 script.py 로 되돌아간다.
        """
        saved = sys.modules.get("submission")
        try:
            good = replay_run.load_module(ROOT / "script.py", "submission")
            with self.assertRaises(OSError):
                replay_run.load_module(ROOT / "없는파일.py", "submission")
            self.assertIs(sys.modules.get("submission"), good)
        finally:
            if saved is None:
                sys.modules.pop("submission", None)
            else:
                sys.modules["submission"] = saved

    def test_failed_first_load_leaves_no_registration(self):
        saved = sys.modules.pop("submission", None)
        try:
            with self.assertRaises(OSError):
                replay_run.load_module(ROOT / "없는파일.py", "submission")
            self.assertNotIn("submission", sys.modules)
        finally:
            if saved is not None:
                sys.modules["submission"] = saved

    def test_replay_reproduces_the_run_csv_byte_for_byte(self):
        """이 검사가 빨개지면 재생 결과를 근거로 쓸 수 없다."""
        self.assertTrue(CASE.is_dir(), f"{CASE} 가 없다")
        result = replay_run.replay(RUN_SCRIPT, CASE, input_path=ROOT / "open/dev.jsonl",
                                   data_dir=ROOT / "open/data")
        produced = replay_run.to_csv_bytes(RUN_SCRIPT, result["rows"])
        self.assertEqual(produced, (CASE / "submission.csv").read_bytes())
        self.assertEqual(len(result["rows"]), 200)
        # 기본 CSV도 같은 응답에서 나오므로 함께 재현돼야 한다.
        self.assertEqual(replay_run.to_csv_bytes(RUN_SCRIPT, result["baseline_rows"]),
                         (CASE / "baseline_submission.csv").read_bytes())
        self.assertEqual(len(result["rejected_conditions"]), 107)

    def test_replay_reproduces_a_run_with_extra_call_phases(self):
        """추가 호출이 켜진 회차도 그 회차의 코드로 재현해야 한다.

        `colab-1789866561858326417`(A1)은 `company_size` 단계를 전건으로 켜고 돈 회차다.
        재생이 `sme` 단계만 알던 동안 같은 성질의 회차 `colab-1789861367622882347`이
        v16 13건·v18 37건 어긋났다 — 원응답에 `split` 155건이 그대로 있었는데 읽지 않았다.
        재생 결과를 근거로 쓰려면 이것이 초록이어야 한다.

        회차 커밋의 코드로 돌린다. HEAD 로 돌리면 HEAD 의 스위치를 따르므로 그 회차의
        재현이 아니라 HEAD 후처리의 측정이 된다 — 둘은 다른 질문이다.
        """
        case = ROOT / "reports/runs/colab-1789866561858326417/dev-debug"
        self.assertTrue(case.is_dir(), f"{case} 가 없다")
        stored = replay_run.saved_responses(case)
        self.assertTrue(stored.get("company_size"), "company_size 단계 원응답이 없다")
        with tempfile.TemporaryDirectory() as tmp:
            run_script = replay_run.run_script(case, tmp)
            result = replay_run.replay(run_script, case, input_path=ROOT / "open/dev.jsonl",
                                       data_dir=ROOT / "open/data")
            self.assertEqual(replay_run.to_csv_bytes(run_script, result["rows"]),
                             (case / "submission.csv").read_bytes())

    def test_refuses_a_run_whose_phases_the_script_cannot_replay(self):
        """모르는 단계를 조용히 건너뛰면 그 단계가 바꾼 판정이 빠진 CSV 를 근거로 쓰게 된다.

        `colab-1789861367622882347`에는 `split` 원응답이 있고 `b113425`의 코드는 그것을
        재생할 줄 모른다. 실제로 한 번 조용히 어긋났으므로 소리를 내야 한다.
        """
        case = ROOT / "reports/runs/colab-1789861367622882347/dev-debug"
        self.assertTrue(replay_run.saved_responses(case).get("split"), "split 원응답이 없다")
        with self.assertRaisesRegex(ValueError, "재생할 줄 모른다"):
            replay_run.replay(RUN_SCRIPT, case, input_path=ROOT / "open/dev.jsonl",
                              data_dir=ROOT / "open/data")

    def test_head_replay_matches_the_pinned_head_csv(self):
        """HEAD 회귀 가드. --verify는 회차 코드로 돌아 HEAD의 parse_judgment·verify_sme·postprocess를
        검사하지 않는다. HEAD 후단을 일부러 바꿨다면 재생 결과를 새로 고정하고 그 이유를 PR에 적는다."""
        result = replay_run.replay(SCRIPT, CASE, input_path=ROOT / "open/dev.jsonl",
                                   data_dir=ROOT / "open/data")
        self.assertEqual(replay_run.to_csv_bytes(SCRIPT, result["rows"]), HEAD_REPLAY.read_bytes())
        # H3의 null 조항 해석을 H2의 unknown/not_required 원응답에 소급하지 않는다.
        h2 = ROOT / "reports/runs/colab-1789894949866134428/dev-debug"
        replayed = replay_run.replay(SCRIPT, h2, input_path=ROOT / "open/dev.jsonl",
                                     data_dir=ROOT / "open/data")
        # `company_size_products()`가 검증된 인용을 요구하면서 이 회차 CSV와 세 셀이 일부러 갈렸다.
        # 보관 CSV는 그 회차가 만든 것이므로 다시 쓰지 않고, 움직인 셀을 여기서 고정한다.
        self.assertEqual(replay_run.csv_cell_diff(replay_run.to_csv_bytes(SCRIPT, replayed["rows"]),
                                                  (h2 / "submission.csv").read_bytes()),
                         [("PPS-DEV-148", "e13"), ("PPS-DEV-16", "v13"), ("PPS-DEV-198", "v13")])

    def test_candidate_replaces_only_the_stage_it_defines(self):
        with tempfile.TemporaryDirectory() as tmp:
            module = Path(tmp) / "candidate.py"
            module.write_text(CANDIDATE, encoding="utf-8", newline="\n")
            candidate = replay_run.load_module(module, "candidate")
            self.assertFalse(hasattr(candidate, "verify_sme"), "후보가 verify_sme를 정의하면 안 된다")
            result = replay_run.replay(RUN_SCRIPT, CASE, input_path=ROOT / "open/dev.jsonl",
                                       data_dir=ROOT / "open/data",
                                       postprocess=candidate.postprocess)
            produced = replay_run.to_csv_bytes(RUN_SCRIPT, result["rows"])
            self.assertNotEqual(produced, (CASE / "submission.csv").read_bytes())
            self.assertTrue(all(row[f"v{i}"] == 0 for row in result["rows"] for i in range(1, 25)))
            # 후보가 안 건드린 단계는 그대로다.
            self.assertEqual(replay_run.to_csv_bytes(RUN_SCRIPT, result["baseline_rows"]),
                             (CASE / "baseline_submission.csv").read_bytes())

    def test_refuses_a_case_without_raw_responses(self):
        with self.assertRaisesRegex(ValueError, "원응답이 없다"):
            replay_run.saved_responses(PLAIN_CASE)
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "가 없다"):
                replay_run.saved_responses(Path(tmp))

    def test_refuses_a_run_whose_document_budget_shrank(self):
        """줄어든 공고의 실제 예산은 토크나이저가 정했고 로그에 건별 값이 없다."""
        with tempfile.TemporaryDirectory() as tmp:
            case = Path(tmp) / "dev-debug"
            case.mkdir()
            shutil.copy(CASE / "diagnostics.jsonl", case / "diagnostics.jsonl")
            report = json.loads((CASE / "run_report.json").read_text(encoding="utf-8"))
            report["sme_documents_shrunk"] = 3
            (case / "run_report.json").write_text(json.dumps(report, ensure_ascii=False),
                                                  encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "재생할 수 없다"):
                replay_run.replay(SCRIPT, case, input_path=ROOT / "open/dev.jsonl",
                                  data_dir=ROOT / "open/data")

    def test_cli_verify_and_output_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "replay"
            base = ["--case", str(CASE), "--input", str(ROOT / "open/dev.jsonl"),
                    "--data-dir", str(ROOT / "open/data")]
            self.assertEqual(replay_run.main(base + ["--verify"]), 0)
            self.assertEqual(replay_run.main(base + ["--verify", "--output-dir", str(out)]), 0)
            record = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
            self.assertIs(record["matches_original"], True)
            self.assertIs(record["model_called"], False)
            self.assertEqual(record["original_sha256"], record["replayed_sha256"])
            self.assertEqual(replay_run.main(base + ["--output-dir", str(out)]), 1, "덮어썼다")
            # 후보 없이 --verify를 빼면 HEAD의 script.py로 재생한다(후보 측정의 기준).
            head = Path(tmp) / "head"
            self.assertEqual(replay_run.main(base + ["--output-dir", str(head)]), 0)
            self.assertEqual((head / "submission.csv").read_bytes(), replay_run.to_csv_bytes(
                SCRIPT, replay_run.replay(SCRIPT, CASE, input_path=ROOT / "open/dev.jsonl",
                                          data_dir=ROOT / "open/data")["rows"]))

            module = Path(tmp) / "candidate.py"
            module.write_text(CANDIDATE, encoding="utf-8", newline="\n")
            # 후보를 넣고 --verify를 하면 "회차와 같다"는 의미가 사라진다.
            self.assertEqual(replay_run.main(base + ["--verify", "--candidate", str(module)]), 1)


class RestoreSpacingHiddenDoc(unittest.TestCase):
    """모델이 못 본 문서의 정확 일치가 **보이는 문서의 복원을 취소하면 안 된다.**

    예산에 잘려 안 보이는 첨부에 무공백 표기가 있으면 `restore_spacing` 이 즉시 None 을
    돌려줬다. 호출자는 원래 인용으로 물러서는데 그것은 `visible` 에 없으므로
    검증된 인용이 통째로 떨어지고 기본 판정이 남는다.
    """

    VISIBLE = "입 찰 방 법 은 전 자 입 찰"
    QUOTE = "입찰방법은전자입찰"

    def test_a_hidden_exact_match_does_not_cancel_a_visible_restoration(self):
        rec = {"docs": [{"text": self.VISIBLE}, {"text": "앞부분 " + self.QUOTE + " 뒷부분"}]}
        self.assertEqual(SCRIPT.restore_spacing(self.QUOTE, rec, self.VISIBLE), self.VISIBLE)

    def test_a_hidden_tail_in_the_same_document_does_not_block_the_search(self):
        """같은 문서의 **잘린 뒷부분**에 정확 일치가 있어도 보이는 앞부분을 찾아야 한다.

        문서 단위로 `quote in text` 를 보면 그 문서를 통째로 건너뛰어 공백 변형을
        찾지도 않고 None 을 돌려줬다 — 첫 수정이 못 막은 자리다.
        """
        text = self.VISIBLE + " 중간채움" * 20 + " " + self.QUOTE
        rec = {"docs": [{"doc_id": "D0", "type": "공고문", "text": text}]}
        visible = SCRIPT.build_context(rec, 45)
        self.assertIn(self.VISIBLE, visible)
        self.assertNotIn(self.QUOTE, visible)
        self.assertEqual(SCRIPT.restore_spacing(self.QUOTE, rec, visible), self.VISIBLE)

    def test_an_exact_match_the_model_saw_still_needs_no_restoration(self):
        text = "앞부분 " + self.QUOTE + " 뒷부분"
        self.assertIsNone(SCRIPT.restore_spacing(self.QUOTE, {"docs": [{"text": text}]}, text))


if __name__ == "__main__":
    unittest.main()
