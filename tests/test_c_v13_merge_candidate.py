"""A-1 v13 경로 합성 후보의 검사.

모델을 부르지 않는다. 운영 판정을 감싼 뒤 **모순되는 보존 경로 하나만** 닫는지,
그리고 그 밖의 어떤 것도 바꾸지 않는지를 고정한다.
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


candidate = load_module("c_v13_merge_candidate",
                        ROOT / "experiments/c_v13_merge_candidate.py")

CASE = ROOT / "reports/runs/colab-1789902969401579900/dev-debug"
DEV = ROOT / "open/dev.jsonl"
LABELS = ROOT / "open/dev_labels.csv"

# 재생으로 실측한 값. HEAD 재생이 기준이며 보관 회차의 submission.csv 가 아니다.
# **베이스가 움직이면 이 값도 움직인다.** `3e3c15d` 에서는 4/9/2 → 4/8/2 였고,
# `c9398ad` 에서 기준 자체가 3/8/3 으로 바뀌었다(16 이 TP 를, 198 이 FP 를 잃었다).
# 후보가 닫는 셀은 그대로 PPS-DEV-03 하나다.
EXPECTED_HEAD = {"tp": 3, "fp": 8, "fn": 3}
EXPECTED_CANDIDATE = {"tp": 3, "fp": 7, "fn": 3}

# **두 수를 구분한다.**
# 적용 대상 = company 가 검증된 scope 를 general 로 확정하고 v13 을 쓰지 않은 공고.
#             그 공고에 명시적 0 을 쓴다. 117건은 이미 0 이라 아무것도 안 바뀐다.
# 셀 변경   = 그중 앞 단계가 양성을 남겨 둔 공고. 여기서만 판정이 실제로 바뀐다.
EXPECTED_APPLICABLE = 118
EXPECTED_CHANGED = ["PPS-DEV-03"]


def load_script():
    return load_module("submission", ROOT / "script.py")


class Unit(unittest.TestCase):
    """운영 반환을 건드리지 않고 한 조건에서만 더한다."""

    def setUp(self):
        self.script = load_script()

    def fake(self, out, reason):
        self.script.verify_company_size = lambda *a, **k: (dict(out), reason)

    def test_adds_zero_when_verified_scope_is_general(self):
        self.fake({"v14": {"위반여부": 0, "근거문구": None}}, "decided")
        out, reason = candidate.verify_company_size({"scope": "general"}, {}, 16000)
        self.assertEqual(out["v13"], {"위반여부": 0, "근거문구": None})
        self.assertEqual(reason, "decided")
        self.assertIn("v14", out, "운영이 낸 다른 키를 잃지 않는다")

    def test_does_nothing_when_scope_is_competitive(self):
        self.fake({"v14": {"위반여부": 0, "근거문구": None}}, "outside_general_scope")
        out, _ = candidate.verify_company_size({"scope": "competitive"}, {}, 16000)
        self.assertNotIn("v13", out, "경쟁제품 scope 에서는 아무것도 가르지 않는다")

    def test_does_nothing_when_scope_is_unverified(self):
        """`unverified_scope` 면 scope 자체가 미확인이다. 기본 판정을 보존한다."""
        self.fake({}, "unverified_scope")
        out, _ = candidate.verify_company_size({"scope": "general"}, {}, 16000)
        self.assertNotIn("v13", out)

    def test_does_not_touch_company_written_v13(self):
        """company 가 조건 충족으로 1 을 썼으면 그대로 둔다."""
        self.fake({"v13": {"위반여부": 1, "근거문구": "인용"}}, "outside_general_scope")
        out, _ = candidate.verify_company_size({"scope": "competitive"}, {}, 16000)
        self.assertEqual(out["v13"]["위반여부"], 1)

    def test_never_raises_item_to_one(self):
        """이 후보는 올리지 않는다. 어떤 입력에서도 v13=1 을 새로 쓰지 않는다."""
        for scope in ("general", "competitive", "other", "unknown", None):
            for reason in ("decided", "outside_general_scope", "unverified_scope"):
                self.fake({}, reason)
                out, _ = candidate.verify_company_size({"scope": scope}, {}, 16000)
                self.assertNotEqual(out.get("v13", {}).get("위반여부"), 1, (scope, reason))

    def test_firing_predicate_matches_the_wiring(self):
        for scope, reason, wrote, expected in (
                ("general", "decided", False, True),
                ("general", "decided", True, False),
                ("general", "unverified_scope", False, False),
                ("competitive", "outside_general_scope", False, False)):
            self.assertIs(candidate.contradicts({"scope": scope}, reason, wrote), expected,
                          (scope, reason, wrote))


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
            cls.truth = {r["id"]: int(r["v13"]) for r in csv.DictReader(stream)}

    def legacy(self):
        out = {}
        script, settings = self.script, self.settings
        if hasattr(script, "DOCUMENT_CHECK_ITEMS") and not settings.get("company_size_document_checks"):
            out["company_size_legacy"] = True
        if hasattr(script, "CLAUSE_QUOTE_MAX"):
            out["company_size_clause_quotes"] = bool(settings.get("company_size_clause_quotes"))
        if hasattr(script, "QUALIFICATION_ROLES"):
            out["company_size_qualification_role"] = bool(settings.get("company_size_qualification_role"))
        return out

    def run_pipeline(self, use_candidate):
        script, legacy = self.script, self.legacy()
        _, products = script.load_sme_reference(str(ROOT / "open/data"))
        verify = candidate.verify_company_size if use_candidate else script.verify_company_size
        out, fired = {}, []
        for rec in script.iter_records(str(DEV)):
            identifier = rec["id"]
            parsed, _ = script.parse_judgment(self.texts["baseline"][identifier])
            for phase in getattr(script, "VERDICT_PHASES", ()):
                script.merge_extra_call(parsed, rec, phase,
                                        script.extra_call_items().get(phase) or (),
                                        self.texts.get(phase, {}).get(identifier))
            sme_text = self.texts.get("sme", {}).get(identifier)
            if sme_text is not None:
                focused, _ = script.parse_judgment(sme_text, expected_items=script.SME_ITEMS, sme=True)
                verified, _rejected = script.verify_sme(focused, rec, products, 16000)
                parsed.update(verified)
            company_text = self.texts.get("company_size", {}).get(identifier)
            if company_text is not None:
                focused, _ = script.parse_judgment(company_text,
                                                   expected_items=script.COMPANY_SIZE_KEYS, **legacy)
                facts = focused["company_size"]
                base_out, reason = script.verify_company_size(facts, rec, self.chars[identifier])
                if candidate.contradicts(facts, reason, "v13" in base_out):
                    fired.append(identifier)      # 적용 대상. 셀이 바뀐다는 뜻은 아니다
                verified, _reason = verify(facts, rec, self.chars[identifier])
                parsed.update(verified)
            done = script.postprocess(parsed, rec)
            out[identifier] = done["v13"]["위반여부"]
        return out, fired

    def score(self, predictions):
        tp = sum(1 for i, v in predictions.items() if v == 1 and self.truth[i] == 1)
        fp = sum(1 for i, v in predictions.items() if v == 1 and self.truth[i] == 0)
        fn = sum(1 for i, v in predictions.items() if v == 0 and self.truth[i] == 1)
        return {"tp": tp, "fp": fp, "fn": fn}

    def test_head_matches_recorded_counts(self):
        head, _ = self.run_pipeline(False)
        self.assertEqual(self.score(head), EXPECTED_HEAD)

    def test_candidate_drops_one_false_positive_and_keeps_every_true_positive(self):
        head, _ = self.run_pipeline(False)
        cand, _ = self.run_pipeline(True)
        self.assertEqual(self.score(cand), EXPECTED_CANDIDATE)
        kept = [i for i, v in head.items() if v == 1 and self.truth[i] == 1]
        for identifier in kept:
            self.assertEqual(cand[identifier], 1, f"{identifier} 의 TP 를 잃었다")

    def test_only_the_expected_notice_changes(self):
        head, _ = self.run_pipeline(False)
        cand, _ = self.run_pipeline(True)
        changed = sorted(i for i in head if head[i] != cand[i])
        self.assertEqual(changed, EXPECTED_CHANGED)

    def test_applicable_is_wide_but_changed_is_one(self):
        """적용 대상과 셀 변경을 갈라 둔다.

        적용 대상이 넓은 것 자체는 위험이 아니다 — 117건은 이미 0 이라 명시적 0 을 써도
        같은 값이다. **위험은 겹침에 있다.** 다른 회차에서 이 118건 중 어느 하나에
        앞 단계 양성이 남으면 그때는 그것도 닫는다. 그 양성이 TP 일 수 있다.
        """
        head, fired = self.run_pipeline(True)
        self.assertEqual(len(fired), EXPECTED_APPLICABLE)
        self.assertIn("PPS-DEV-03", fired)
        base, _ = self.run_pipeline(False)
        changed = sorted(i for i in base if base[i] != head[i])
        self.assertEqual(changed, EXPECTED_CHANGED)
        self.assertLess(len(changed), len(fired), "적용 대상과 셀 변경은 다른 수다")


if __name__ == "__main__":
    unittest.main()
