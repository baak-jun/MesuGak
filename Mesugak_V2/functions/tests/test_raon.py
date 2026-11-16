import json
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from jobs.ask_raon import build_request, request_opinion


class RaonTest(unittest.TestCase):
    def test_input_keeps_indicators_and_excludes_account(self):
        payload = {"code": "005930", "lastDate": "2026-10-21", "account": "private",
                   "history": [{"date": "2026-10-21", "rsi": None, "ma120": 10, "secret": "private"}] * 140}
        request = build_request(payload)
        analysis = json.loads(request["messages"][1]["content"])["analysis"]
        self.assertEqual(len(analysis["history"]), 130)
        self.assertIsNone(analysis["history"][-1]["rsi"])
        self.assertEqual(analysis["history"][-1]["ma120"], 10)
        self.assertNotIn("private", json.dumps(request))

    def test_summary_rejected(self):
        with self.assertRaises(ValueError):
            build_request({"code": "005930", "lastDate": "2026-10-21"})

    @patch("requests.post")
    def test_one_request_no_reasoning_saved(self, post):
        post.return_value = Mock(status_code=200)
        post.return_value.json.return_value = {"choices": [{"finish_reason": "stop", "message": {"content": "opinion", "reasoning": "hidden"}}]}
        result = request_opinion({}, "dummy-key")
        self.assertEqual(result["opinion"], "opinion")
        self.assertNotIn("hidden", json.dumps(result))
        post.assert_called_once()
        self.assertFalse(post.call_args.kwargs["allow_redirects"])

    @patch("requests.post")
    def test_rate_limit_does_not_retry_or_echo_body(self, post):
        post.return_value = Mock(status_code=429, text="dummy-secret")
        with self.assertRaisesRegex(RuntimeError, "HTTP 429"):
            request_opinion({}, "dummy-key")
        post.assert_called_once()

    @patch("requests.post")
    def test_truncated_answer_rejected(self, post):
        post.return_value = Mock(status_code=200)
        post.return_value.json.return_value = {"choices": [{"finish_reason": "length", "message": {"content": "partial"}}]}
        with self.assertRaisesRegex(RuntimeError, "truncated"):
            request_opinion({}, "dummy-key")


if __name__ == "__main__":
    unittest.main()
