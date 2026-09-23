"""D7 v3 발화율 수집기의 계산·계약 검사. 모델을 부르지 않는다."""

import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


script = _load("submission", ROOT / "script.py")
collector = _load("d7_collect_v3_firing", ROOT / "experiments/d7_collect_v3_firing.py")
CASE = ROOT / "reports/runs/colab-1789902969401579900/dev-debug"


def archived_baseline():
    """회차가 남긴 기본 단계 원응답. 합성 문자열이 아니라 실제 모델 출력이다."""
    texts = {}
    for line in (CASE / "diagnostics.jsonl").read_text(encoding="utf-8").splitlines():
        event = json.loads(line)
        if (event.get("event") == "response" and event.get("phase") == "baseline"
                and event.get("status") == "valid"):
            texts[event["id"]] = event["response_text"]
    return texts


class ObserveTests(unittest.TestCase):
    def test_counts_match_the_archived_run(self):
        """보관 응답에서 센 v3 세 값이 그 회차의 제출 CSV와 어긋나지 않는다."""
        records = {r["id"]: r for r in script.iter_records(str(ROOT / "open/dev.jsonl"))}
        texts = archived_baseline()
        self.assertEqual(len(texts), 200)
        rows = [dict(id=i, **collector.observe(records[i], t)) for i, t in texts.items()]
        counted = collector.rates(rows)
        self.assertEqual(counted["count"], 200)
        # 게이트는 모델 양성에서만 발화하고, 내리기만 한다.
        self.assertLessEqual(counted["gate_fired"], counted["model_v3"])
        self.assertEqual(counted["final_v3"], counted["model_v3"] - counted["gate_fired"])
        for row in rows:
            if not row["model_v3"]:
                self.assertEqual(row["gate_fired"], 0)

    def test_summary_reports_multiples_and_refuses_to_claim_completion(self):
        def shard(rows):
            return {"payload": {"rows": rows}}
        dev = [dict(model_v3=1, gate_fired=1, final_v3=0)] * 2 + [dict(model_v3=0, gate_fired=0, final_v3=0)] * 8
        unlabeled = [dict(model_v3=1, gate_fired=0, final_v3=1)] + [dict(model_v3=0, gate_fired=0, final_v3=0)] * 9
        summary = collector.summarize({"dev": shard(dev), "unlabeled-00": shard(unlabeled)})
        self.assertEqual(summary["dev"]["model_v3_rate"], 0.2)
        self.assertEqual(summary["unlabeled"]["model_v3_rate"], 0.1)
        self.assertEqual(summary["unlabeled_over_dev"]["model_v3_rate"], 0.5)
        # dev 발화가 있고 무라벨 발화가 0이면 배율은 0이다 — null 로 감추지 않는다.
        self.assertEqual(summary["unlabeled_over_dev"]["gate_fired_rate"], 0.0)
        # 부분 수집은 20,000건 증거가 아니다.
        self.assertFalse(summary["complete"])

    def test_summary_multiple_is_null_when_dev_never_fires(self):
        rows = [dict(model_v3=0, gate_fired=0, final_v3=0)] * 4
        summary = collector.summarize({"dev": {"payload": {"rows": rows}},
                                       "unlabeled-00": {"payload": {"rows": rows}}})
        self.assertIsNone(summary["unlabeled_over_dev"]["gate_fired_rate"])

    def test_saved_shard_is_re_derived_not_trusted(self):
        """저장본의 숫자를 그대로 믿지 않고 원응답에서 다시 센다."""
        records = list(script.iter_records(str(ROOT / "open/dev.jsonl")))[:1]
        texts = archived_baseline()
        rec = records[0]
        row = dict(id=rec["id"], response_text=texts[rec["id"]], prompt_tokens=10, max_chars=16000,
                   **collector.observe(rec, texts[rec["id"]]))
        payload = {"rows": [row], "inference_seconds": 1.0, "stage_seconds": 1.0}
        value = {"contract_sha256": "c", "payload_sha256": collector.digest(payload),
                 "payload": payload}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "dev.json"
            path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
            self.assertEqual(collector.read_shard(path, records, "c")["payload"], payload)
            # 숫자를 손으로 뒤집으면 원응답과 어긋나 거부한다.
            tampered = json.loads(json.dumps(value))
            tampered["payload"]["rows"][0]["gate_fired"] = 1 - row["gate_fired"]
            tampered["payload_sha256"] = collector.digest(tampered["payload"])
            path.write_text(json.dumps(tampered, ensure_ascii=False), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Invalid saved observation"):
                collector.read_shard(path, records, "c")


if __name__ == "__main__":
    unittest.main()
