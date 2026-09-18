"""API 러너 검사. 실제 호출은 하지 않는다 — 전송 계층만 갈아 끼운다."""

import importlib.util
import io
import json
from pathlib import Path
import re
import tempfile
import time
import unittest
from unittest import mock
import urllib.error

ROOT = Path(__file__).resolve().parents[1]


def _load(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


api_run = _load("api_run", "tools/api_run.py")
package_tool = _load("package_tool", "tools/package.py")
baseline = _load("baseline", "script.py")

MESSAGES = [{"role": "system", "content": "역할"}, {"role": "user", "content": "공고"}]


class Stub(api_run.APIRunner):
    """망을 타지 않는 러너. RESPONSE가 없으면 호출이 실패한 것으로 둔다."""

    KEY = "test-key"
    TPM = 10 ** 9
    RESPONSE = None

    def _post(self, url, body):
        self.sent = body
        if self.RESPONSE is None:
            raise ValueError("HTTP 429: quota exceeded")
        return self.RESPONSE


def answer(text, thought=None):
    parts = ([{"text": thought, "thought": True}] if thought else []) + [{"text": text}]
    return {"candidates": [{"content": {"parts": parts}, "finishReason": "STOP"}],
            "usageMetadata": {"promptTokenCount": 11, "candidatesTokenCount": 7},
            "modelVersion": "gemma-4-26b-a4b-it", "responseId": "abc"}


class ApiRunTest(unittest.TestCase):
    def test_pacer_waits_for_the_window_but_lets_an_oversized_call_through(self):
        bucket = api_run.TokenBucket(100, window=0.3)
        started = time.time()
        bucket.take(60)
        bucket.take(60)          # 120 > 100 이므로 창이 지나갈 때까지 기다려야 한다.
        self.assertGreaterEqual(time.time() - started, 0.25)
        api_run.TokenBucket(100, window=30).take(5000)  # 한 건이 상한보다 커도 멈추지 않는다.

    def test_rate_limit_wait_comes_from_the_body_not_from_backoff(self):
        """429 본문의 남은 창은 400자쯤 뒤에 있다. 앞부분만 보면 영영 못 찾는다."""
        body = ('{"error": {"code": 429, "message": "You exceeded your current quota. '
                + "x" * 350 + 'Please retry in 41.9s."}}')
        url = "https://example.invalid/v1beta/models/x:countTokens"
        answers = [urllib.error.HTTPError(url, 429, "err", {}, io.BytesIO(body.encode("utf-8"))),
                   io.BytesIO(b'{"totalTokens": 9}')]

        def fake_urlopen(request, timeout=None):
            got = answers.pop(0)
            if isinstance(got, Exception):
                raise got
            return got

        runner = Stub.__new__(Stub)
        with mock.patch.object(api_run.urllib.request, "urlopen", fake_urlopen), \
                mock.patch.object(api_run.time, "sleep") as slept:
            self.assertEqual(api_run.APIRunner._post(runner, url, {}), {"totalTokens": 9})
        self.assertAlmostEqual(slept.call_args[0][0], 42.9, places=1)

    def test_the_real_limit_is_read_from_the_quota_body(self):
        """Gemma는 공식 요금제 표에 행이 없다. 429가 알려 주는 값이 유일한 사실이다."""
        runner = Stub(baseline.decode_schema(str(ROOT / "open/data")))
        runner._adopt_limit("...input_token_count, limit: 400000, model: gemma-4-26b...")
        self.assertEqual(runner.bucket.per_minute, 400000)
        runner._adopt_limit('"quotaId": "RequestsPerMinute", limit: 30, model: gemma-4-26b')
        self.assertEqual(runner.bucket.per_minute, 400000)  # 다른 할당량의 숫자는 안 가져온다.

    def test_request_puts_the_system_turn_in_system_instruction(self):
        body = api_run.to_request(MESSAGES)
        self.assertEqual(body["systemInstruction"], {"parts": [{"text": "역할"}]})
        self.assertEqual(body["contents"], [{"role": "user", "parts": [{"text": "공고"}]}])

    def test_answer_drops_thought_parts_and_records_usage(self):
        runner = Stub(baseline.decode_schema(str(ROOT / "open/data")))
        runner.RESPONSE = answer('{"v1": 1}', thought="생각 채널")
        self.assertEqual(runner.chat([MESSAGES]), ['{"v1": 1}'])
        info = runner.last_response_info[0]
        self.assertEqual((info["prompt_tokens"], info["response_id"]), (11, "abc"))
        self.assertEqual((runner.calls, runner.tokens["prompt"]), (1, 11))

    def test_focused_call_restricts_the_schema_to_the_asked_items(self):
        runner = Stub(baseline.decode_schema(str(ROOT / "open/data")))
        runner.SCRIPT, runner.RESPONSE = baseline, answer("{}")
        runner.chat([MESSAGES], items=baseline.SME_ITEMS)
        schema = runner.sent["generationConfig"]["responseJsonSchema"]
        self.assertEqual(set(schema["properties"]), set(baseline.SME_ITEMS))
        self.assertIn("facts", schema["properties"]["v13"]["properties"])
        # 원본 스키마는 그대로 둔다. 좁힌 것이 남으면 다음 공고가 24항목을 못 받는다.
        self.assertIn("v1", runner.sp.structured_outputs.json["properties"])

    def test_runaway_answer_recovers_through_the_submission_split_retry(self):
        """API의 responseJsonSchema는 maxLength를 안 지킨다. 근거 문자열에서 폭주하면
        2048토큰을 다 쓰고 JSON이 안 닫힌다 — dev 200건 회차가 PPS-DEV-08에서 이렇게 죽었다.
        복구는 제출 코드의 6개·1개 분할이 한다."""
        runner = Stub(baseline.decode_schema(str(ROOT / "open/data")))
        runner.SCRIPT = baseline
        asked = []

        def answers(url, body):
            if url.endswith("countTokens"):     # 분할 재시도는 건마다 예산을 다시 센다.
                return {"totalTokens": 11000}
            keys = list(body["generationConfig"]["responseJsonSchema"]["properties"])
            asked.append(keys)
            if len(keys) == 24:      # 통짜 호출은 폭주해서 JSON이 안 닫힌다.
                return answer('{"v1":{"위반여부":0,"근거문구":"' + "폭주 " * 400)
            return answer(json.dumps({k: {"위반여부": 0, "근거문구": None} for k in keys},
                                     ensure_ascii=False))

        runner._post = answers
        with self.assertRaises(ValueError):                      # 통짜는 파싱에서 막힌다.
            baseline.parse_judgment(runner.chat([MESSAGES])[0])
        merged = json.loads(runner.retry_chat([MESSAGES])[0])
        self.assertEqual(set(merged), set(baseline.ITEMS))       # 24항목이 다 모인다.
        self.assertEqual([len(k) for k in asked[1:]], [6, 6, 6, 6])
        self.assertEqual(runner.last_response_info[0]["retry_strategy"], "split_items")

    def test_failed_call_surfaces_the_api_error_instead_of_a_field_collision(self):
        """`error_type`·`error_message`는 run_chunk의 record()가 자기 인자로 쓴다."""
        runner = Stub(baseline.decode_schema(str(ROOT / "open/data")))
        self.assertEqual(runner.chat([MESSAGES]), [""])
        self.assertEqual(runner.last_response_info[0]["api_error_message"], "HTTP 429: quota exceeded")
        with self.assertRaises(RuntimeError) as caught:
            baseline.run_chunk(runner, [MESSAGES], ids=["PPS-DEV-01"])
        self.assertIn("429", str(caught.exception))

    def test_no_key_falls_back_to_mock_and_says_so(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "run"
            self.assertEqual(api_run.main(["--output-dir", str(out), "--limit", "1", "--mock"]), 0)
            manifest = json.loads((out / "api-run.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["mode"], "mock")
            self.assertFalse(manifest["counts_as_r4_normal_call"])
            report = json.loads((out / "run_report.json").read_text(encoding="utf-8"))
            self.assertEqual((report["mode"], report["model_success_count"]), ("mock", 0))

    def test_api_path_never_reaches_the_submission_zip(self):
        """R7: 제출 추론에 외부 호출이 없어야 한다. 제출물은 두 파일뿐이다."""
        self.assertEqual(package_tool.FILES, ("script.py", "requirements.txt"))
        source = (ROOT / "script.py").read_text(encoding="utf-8")
        # 주석으로 가리키는 것은 괜찮다. 실제로 **부르는 것**이 금지다.
        forbidden = r"^\s*(?:import|from)\s+(?:api_run|urllib|requests|httpx|socket|http)\b"
        self.assertEqual(re.findall(forbidden, source, re.M), [])


if __name__ == "__main__":
    unittest.main()
