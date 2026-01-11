import json
import tempfile
import unittest
from pathlib import Path

from src.agents.retention_agent.feedback_logger import FeedbackEvent, FeedbackLogger


class TestRetentionFeedbackLogger(unittest.TestCase):
    def test_log_writes_jsonl(self):
        with tempfile.TemporaryDirectory() as td:
            log_path = Path(td) / "retention_feedback.jsonl"
            logger = FeedbackLogger(log_path=log_path)

            e = FeedbackEvent(
                timestamp_utc=FeedbackLogger.now_utc_iso(),
                customer_id="CUST_003",
                recommended_action="draft_reengagement",
                action_taken="accepted",
                notes="CSM will send message tomorrow",
                churn_score=0.91,
                confidence=0.85,
            )

            logger.log(e)

            self.assertTrue(log_path.exists())
            lines = log_path.read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(len(lines), 1)

            obj = json.loads(lines[0])
            self.assertEqual(obj["customer_id"], "CUST_003")
            self.assertEqual(obj["action_taken"], "accepted")
            self.assertEqual(obj["recommended_action"], "draft_reengagement")


if __name__ == "__main__":
    unittest.main()
