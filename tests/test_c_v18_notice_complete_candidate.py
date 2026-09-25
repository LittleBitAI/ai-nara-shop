"""A v16·v18 공고문 완전관측 게이트 후보의 검사 — **반려된 후보의 동작 기록**이다.

이 후보는 **반려됐다.** `docs/data.md:48` 이 "위반이 첨부에만 나타날 수 있으므로 공고문만으로
판단을 끝내지 않습니다" 라고 정한 데이터 계약과 충돌하기 때문이다. 사유 셋은
`reports/team-c/a-v18-notice-complete/README.md` §0 에 있다.

**따라서 아래 검사는 "이렇게 동작해야 한다"는 요구가 아니라 "이렇게 동작했다"는 기록이다.**
특히 첨부 절단을 통과시키는 검사는 계약 위반을 승인하는 것이 아니라 **반려 사유가 된 그
동작을 눈에 보이게 고정**해 두는 것이다. 이 후보를 살리는 변형을 만들지 않는다.

파일과 검사를 지우지 않는 이유는 반려 근거를 재현 가능하게 남기기 위해서다.

모델을 부르지 않는다.
"""

from __future__ import annotations

import csv
import importlib.util
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def load_module(name, path):
    """`sys.path` 를 고친 뒤 실어야 하므로 모듈 최상단 import 를 쓰지 않는다."""
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


candidate = load_module("c_v18_notice_complete_candidate",
                        ROOT / "experiments/c_v18_notice_complete_candidate.py")

CASE = ROOT / "reports/runs/colab-1789902969401579900/dev-debug"
DEV = ROOT / "open/dev.jsonl"
LABELS = ROOT / "open/dev_labels.csv"
ITEMS = ["v14", "v15", "v16", "v17", "v18"]

# 재생으로 실측한 값. 기준은 HEAD 재생이며 보관 회차의 submission.csv 가 아니다.
# 기준 commit 37fe53e. c9398ad·1b34786 에서도 같은 값이었다 — 베이스 세 지점에서 불변이다.
# v17 은 운영 v17 인용 게이트(`v17_quote_is_narrow`)가 FP 넷(038·102·120·172)을 내려 6 → 2 다.
EXPECTED_CANDIDATE = {"v14": (7, 2, 1), "v15": (4, 1, 2), "v16": (4, 3, 2),
                      "v17": (5, 2, 1), "v18": (2, 1, 5)}  # v18: the facts dev-fit zeroes 3 no-bid FPs
# The rule is ported into script.py (feat/b-dev-gain-bundle), so HEAD now equals the candidate.
# Measured before the port: HEAD v16 (4, 2, 2) · v18 (1, 2, 6), and the candidate moved exactly
# ("PPS-DEV-22", "v18") TP · ("PPS-DEV-132", "v16") · ("PPS-DEV-163", "v18") · ("PPS-DEV-195", "v18").
EXPECTED_HEAD = EXPECTED_CANDIDATE
EXPECTED_CHANGED = set()


def load_script():
    return load_module("submission", ROOT / "script.py")


class Unit(unittest.TestCase):
    """게이트 술어와 감싸기 계약."""

    def setUp(self):
        self.script = load_script()

    def fake(self, out, reason):
        self.script.verify_company_size = lambda *a, **k: (dict(out), reason)

    def rec(self, notice="공고문 전문", extra=None, complete=True):
        docs = [{"type": "공고문", "doc_id": "D0", "text": notice}]
        if extra is not None:
            docs.append({"type": "과업지시서", "doc_id": "D1", "text": extra})
        return {"id": "T", "docs": docs, "input_completeness": {"완전관측": complete}}

    def test_untouched_when_reason_is_not_blocked(self):
        """운영이 다른 사유를 냈으면 한 글자도 바꾸지 않는다."""
        for reason in ("decided", "outside_general_scope", "unverified_scope",
                       "unverified_qualification", "unknown_price"):
            self.fake({"v14": {"위반여부": 0, "근거문구": None}}, reason)
            out, got = candidate.verify_company_size({}, self.rec(), 16000)
            self.assertEqual(got, reason)
            self.assertEqual(out, {"v14": {"위반여부": 0, "근거문구": None}})

    def test_notice_complete_requires_a_notice(self):
        """공고문이 없으면 거짓이다. 제한사항의 명시 장소가 공고문이기 때문이다."""
        rec = {"id": "T", "docs": [{"type": "과업지시서", "doc_id": "D1", "text": "본문"}],
               "input_completeness": {"완전관측": True}}
        self.assertFalse(candidate.notice_complete({"qualification_complete": "yes"}, rec, "본문"))

    def test_notice_complete_requires_full_notice_text(self):
        """공고문이 한 조각이라도 잘리면 거짓이다. 절단을 부재로 읽지 않는다."""
        facts = {"qualification_complete": "yes"}
        rec = self.rec(notice="가나다라마바사")
        self.assertTrue(candidate.notice_complete(facts, rec, "머리\n가나다라마바사\n꼬리"))
        self.assertFalse(candidate.notice_complete(facts, rec, "머리\n가나다라마"))

    def test_notice_complete_requires_both_flags(self):
        facts = {"qualification_complete": "yes"}
        self.assertTrue(candidate.notice_complete(facts, self.rec(), "공고문 전문"))
        self.assertFalse(candidate.notice_complete(facts, self.rec(complete=False), "공고문 전문"))
        self.assertFalse(candidate.notice_complete({"qualification_complete": "no"},
                                                   self.rec(), "공고문 전문"))

    def test_truncated_attachment_no_longer_blocks(self):
        """**반려 사유가 된 동작이다.** 공고문이 온전하면 첨부 절단을 통과시킨다.

        `docs/data.md:48` 은 "위반이 첨부에만 나타날 수 있으므로 공고문만으로 판단을
        끝내지 않습니다" 라고 정한다. 이 검사는 그 계약을 승인하지 않는다 —
        후보가 계약을 어긴 **지점을 고정해** 반려 근거를 재현 가능하게 남긴다.
        """
        facts = {"qualification_complete": "yes"}
        rec = self.rec(notice="공고문 전문", extra="과업지시서 앞부분과 잘린 꼬리")
        visible = "공고문 전문\n\n과업지시서 앞부분"   # 꼬리가 없다
        self.assertTrue(candidate.notice_complete(facts, rec, visible))


class ReplayStoredRun(unittest.TestCase):
    """보관 회차의 원응답으로 전 경로를 태워 실측값을 고정한다."""

    @classmethod
    def setUpClass(cls):
        if not (CASE / "diagnostics.jsonl").is_file():
            raise unittest.SkipTest(f"{CASE} 가 없다")
        cls.script = load_script()
        cls.script.load_sme_reference(str(ROOT / "open/data"))
        settings = json.loads((CASE / "run_report.json").read_text(encoding="utf-8"))
        cls.settings = settings["reproduction"]["settings"]
        cls.texts, cls.chars = {}, {}
        for line in (CASE / "diagnostics.jsonl").read_text(encoding="utf-8").splitlines():
            event = json.loads(line)
            if (event.get("event") == "response" and event.get("status") == "valid"
                    and "response_text" in event):
                cls.texts.setdefault(event["phase"], {})[event["id"]] = event["response_text"]
            if event.get("event") == "company_size_input":
                cls.chars[event["id"]] = event["max_chars"]
        with LABELS.open(encoding="utf-8", newline="") as stream:
            cls.truth = {r["id"]: r for r in csv.DictReader(stream)}
        cls.head = cls.run_pipeline(use_candidate=False)
        cls.cand = cls.run_pipeline(use_candidate=True)

    @classmethod
    def legacy(cls):
        out, script, settings = {}, cls.script, cls.settings
        if hasattr(script, "DOCUMENT_CHECK_ITEMS") and not settings.get("company_size_document_checks"):
            out["company_size_legacy"] = True
        if hasattr(script, "CLAUSE_QUOTE_MAX"):
            out["company_size_clause_quotes"] = bool(settings.get("company_size_clause_quotes"))
        if hasattr(script, "QUALIFICATION_ROLES"):
            out["company_size_qualification_role"] = bool(settings.get("company_size_qualification_role"))
        return out

    @classmethod
    def run_pipeline(cls, use_candidate):
        script, legacy = cls.script, cls.legacy()
        _, products = script.load_sme_reference(str(ROOT / "open/data"))
        verify = candidate.verify_company_size if use_candidate else script.verify_company_size
        out = {}
        for rec in script.iter_records(str(DEV)):
            identifier = rec["id"]
            parsed, _ = script.parse_judgment(cls.texts["baseline"][identifier])
            for phase in getattr(script, "VERDICT_PHASES", ()):
                script.merge_extra_call(parsed, rec, phase,
                                        script.extra_call_items().get(phase) or (),
                                        cls.texts.get(phase, {}).get(identifier))
            sme_text = cls.texts.get("sme", {}).get(identifier)
            if sme_text is not None:
                focused, _ = script.parse_judgment(sme_text, expected_items=script.SME_ITEMS, sme=True)
                verified, _rejected = script.verify_sme(focused, rec, products, 16000)
                parsed.update(verified)
            company_text = cls.texts.get("company_size", {}).get(identifier)
            if company_text is not None:
                focused, _ = script.parse_judgment(company_text,
                                                   expected_items=script.COMPANY_SIZE_KEYS, **legacy)
                verified, _reason = verify(focused["company_size"], rec, cls.chars[identifier])
                parsed.update(verified)
            out[identifier] = script.postprocess(parsed, rec)
        return out

    def score(self, predictions, item):
        tp = fp = fn = 0
        for i, row in predictions.items():
            t, h = int(self.truth[i][item]), int(row[item]["위반여부"])
            tp += t == h == 1
            fp += t == 0 and h == 1
            fn += t == 1 and h == 0
        return (tp, fp, fn)

    def test_head_matches_measured_baseline(self):
        for item, expected in EXPECTED_HEAD.items():
            self.assertEqual(self.score(self.head, item), expected, item)

    def test_candidate_matches_measured_result(self):
        for item, expected in EXPECTED_CANDIDATE.items():
            self.assertEqual(self.score(self.cand, item), expected, item)

    def test_changed_cells_are_none_after_the_port(self):
        # 정답 CSV 는 e1~e24 근거 열도 들고 있다. 판정 열만 센다.
        changed = {(i, v) for i in self.head for v in self.script.ITEMS
                   if self.head[i][v]["위반여부"] != self.cand[i][v]["위반여부"]}
        self.assertEqual(changed, EXPECTED_CHANGED)

    def test_no_cell_outside_the_five_items_moves(self):
        """대상 밖 0셀. 다섯 항목 말고는 한 칸도 안 움직인다."""
        for i in self.head:
            for v in self.script.ITEMS:
                if v in ITEMS:
                    continue
                self.assertEqual(self.head[i][v]["위반여부"], self.cand[i][v]["위반여부"], (i, v))

    def test_only_raises_never_lowers(self):
        """이 후보는 보류를 푸는 것이라 0→1 만 낸다. 1→0 은 없다."""
        for i in self.head:
            for v in ITEMS:
                before, after = self.head[i][v]["위반여부"], self.cand[i][v]["위반여부"]
                self.assertFalse(before == 1 and after == 0, (i, v))

    def test_no_true_positive_is_lost(self):
        """다섯 항목의 기존 TP 를 하나도 잃지 않는다."""
        for i in self.head:
            for v in ITEMS:
                if int(self.truth[i][v]) == 1 and self.head[i][v]["위반여부"] == 1:
                    self.assertEqual(self.cand[i][v]["위반여부"], 1, (i, v))


if __name__ == "__main__":
    unittest.main()
