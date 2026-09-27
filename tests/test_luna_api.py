"""The Luna labeler records only completed responses. No network: `post` is replaced."""

import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("luna_api", ROOT / "tools/luna_api.py")
luna_api = importlib.util.module_from_spec(spec)
spec.loader.exec_module(luna_api)


def response(status, text='{"ok": 1}'):
    return {"status": status, "incomplete_details": {"reason": "max_output_tokens"} if status != "completed" else None,
            "output": [{"type": "message", "content": [{"type": "output_text", "text": text}]}],
            "usage": {"input_tokens": 10, "output_tokens": 5}}


class AskTest(unittest.TestCase):
    def setUp(self):
        self.original = luna_api.post

    def tearDown(self):
        luna_api.post = self.original

    def test_an_incomplete_response_is_a_failure_even_with_parseable_text(self):
        luna_api.post = lambda payload, timeout: response("incomplete")
        with self.assertRaisesRegex(ValueError, "incomplete"):
            luna_api.ask("context", "notice")

    def test_a_completed_response_becomes_an_envelope_with_its_status(self):
        luna_api.post = lambda payload, timeout: response("completed")
        envelope = json.loads(luna_api.ask("context", "notice"))
        self.assertEqual((envelope["result"], envelope["status"]), ('{"ok": 1}', "completed"))

    def test_the_context_carries_the_cache_breakpoint_and_the_notice_does_not(self):
        payload = luna_api.body("context", "notice", "gpt-6-luna", "high")
        developer, user = payload["input"]
        self.assertIn("prompt_cache_breakpoint", developer["content"][0])
        self.assertNotIn("prompt_cache_breakpoint", user["content"][0])


if __name__ == "__main__":
    unittest.main()
