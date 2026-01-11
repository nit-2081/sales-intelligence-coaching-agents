import json
import tempfile
import unittest
from pathlib import Path

from src.agents.negotiator_agent.feedback_logger import FeedbackLogger


class TestNegotiatorFeedbackLogger(unittest.TestCase):
    def test_log_writes_jsonl(self):
        with tempfile.TemporaryDirectory() as td:
            log_path = Path(td) / "neg_feedback.jsonl"
            logger = FeedbackLogger(log_path=log_path)

            logger.log(
                call_id="neg_call_01",
                chunk_id=3,
                rep_action="accepted",
                objection="price",
                sentiment_label="negative",
                confidence=0.82,
                strength="strong",
                generation_path="llm",
            )

            self.assertTrue(log_path.exists())
            lines = log_path.read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(len(lines), 1)

            obj = json.loads(lines[0])
            self.assertEqual(obj["agent"], "negotiator_agent")
            self.assertEqual(obj["rep_action"], "accepted")
            self.assertEqual(obj["objection"], "price")

    def test_invalid_action_raises(self):
        with tempfile.TemporaryDirectory() as td:
            log_path = Path(td) / "neg_feedback.jsonl"
            logger = FeedbackLogger(log_path=log_path)

            with self.assertRaises(ValueError):
                logger.log(
                    call_id="neg_call_01",
                    chunk_id=1,
                    rep_action="clicked",  # invalid
                    objection="none",
                    sentiment_label="neutral",
                    confidence=0.6,
                    strength="soft",
                    generation_path="fallback",
                )


if __name__ == "__main__":
    unittest.main()
