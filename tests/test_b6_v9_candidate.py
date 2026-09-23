"""B6 v9 후보 검사. 모델을 부르지 않는다. live 성능 검사가 아니다.

착수서(`docs/tasks/b-v9-equivalent-gate.md`)의 통과 조건 두 가지를 지킨다 —
H1 이 바꾼 e9 는 `clean_evidence()` 를 통과하고, 지정 문장이 `공고문` 에만 있는 공고를 H1 이 내리지 않는다.
판정 표의 지정·지정 아님 꼴도 함께 고정한다.
"""

import importlib.util
import os
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


script = _load("submission", ROOT / "script.py")
script.load_sme_reference(str(ROOT / "open/data"))
candidate = _load("b6_v9_candidate", ROOT / "experiments" / "b6_v9_candidate.py")


def record(docs, dropped=None):
    return {"id": "T-1", "docs": [{"doc_id": str(n), "type": t, "text": x} for n, (t, x) in enumerate(docs)],
            "dropped_doc_counts": dropped or {}, "meta": {}}


def judged(quote):
    cells = {v: {"위반여부": 0, "근거문구": None} for v in script.ITEMS}
    cells["v9"] = {"위반여부": 1, "근거문구": quote}
    return cells


class DesignationTable(unittest.TestCase):
    def test_designations(self):
        for line in ["- 제조사·모델명 : 아크론브라스(Akron Brass) 터보젯(TurboJet)", "모 델 : DH360/300C",
                     "Agilent ICP-OES 5900", "DJI RC PLUS 2(조종기) 1개", "모델 : 현대 유니버스 수소전기버스"]:
            self.assertIsNotNone(candidate.designation_kind(line), line)

    def test_not_designations(self):
        for line in ["Maxwell 7칩이 내장된 Pro-point 처리기술을 이용하여", "국가정보원 CC인증 EAL4 必",
                     "친환경 eVGT 엔진(Tier-5)", "모델명: ____", "제안 모델명 : 가나", "CPU 성능 3.0GHz 이상",
                     "- 길이 : 195mm", "[지역:r1|단위=기초|광역=경기도] 조달청 나라장터"]:
            self.assertIsNone(candidate.designation_kind(line), line)


class H1(unittest.TestCase):
    def setUp(self):
        os.environ["B6_MODE"] = "h1"

    def tearDown(self):
        os.environ.pop("B6_MODE", None)

    def test_designation_only_in_notice_is_kept_and_quoted(self):
        rec = record([("공고문", "1. 구매 물품\n모델명 : Vanquish Core HPLC\n"),
                      ("규격서", "IRU는 광섬유 방식으로 교체\n")])
        out = candidate.postprocess(judged("IRU는 광섬유 방식으로 교체"), rec)
        self.assertEqual(out["v9"]["위반여부"], 1)
        ev = out["v9"]["근거문구"]
        self.assertEqual(ev, "모델명 : Vanquish Core HPLC")
        self.assertEqual(ev, script.clean_evidence(ev, rec["docs"][0]["text"]))

    def test_no_designation_anywhere_is_dropped(self):
        rec = record([("규격서", "IRU는 광섬유 방식으로 교체\n")])
        self.assertEqual(candidate.postprocess(judged("IRU는 광섬유 방식으로 교체"), rec)["v9"]["위반여부"], 0)

    def test_dropped_attachment_is_not_evidence_of_absence(self):
        rec = record([("규격서", "IRU는 광섬유 방식으로 교체\n")], dropped={"제안요청서": 1})
        self.assertEqual(candidate.postprocess(judged("IRU는 광섬유 방식으로 교체"), rec)["v9"]["위반여부"], 1)


if __name__ == "__main__":
    unittest.main()
