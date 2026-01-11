import unittest

from src.agents.negotiator_agent.output_formatter import OutputFormatter
from src.agents.negotiator_agent.decision_engine import WhisperDecision


class TestOutputFormatter(unittest.TestCase):
    def setUp(self) -> None:
        self.fmt = OutputFormatter()

    def test_returns_none_when_no_whisper(self):
        d = WhisperDecision(
            call_id="c1",
            chunk_id=1,
            should_whisper=False,
            confidence=0.0,
            strength="none",
            generation_path="none",
            objection="none",
            sentiment_label="neutral",
            sentiment_confidence=0.4,
            suggested_reply=None,
            tone=None,
            reason="no_trigger",
            debug={},
        )
        self.assertIsNone(self.fmt.format(d))

    def test_formats_whisper_card(self):
        d = WhisperDecision(
            call_id="c1",
            chunk_id=2,
            should_whisper=True,
            confidence=0.82,
            strength="strong",
            generation_path="llm",
            objection="price",
            sentiment_label="negative",
            sentiment_confidence=0.85,
            suggested_reply="Totally fair — what budget range are you aiming for?",
            tone="curious",
            reason="llm_ok",
            debug={"computed_confidence": 0.82},
        )
        card = self.fmt.format(d)
        self.assertIsNotNone(card)
        self.assertEqual(card["call_id"], "c1")
        self.assertEqual(card["whisper"]["objection"], "price")
        self.assertIn("confidence", card)
        self.assertIn("debug", card)


if __name__ == "__main__":
    unittest.main()
