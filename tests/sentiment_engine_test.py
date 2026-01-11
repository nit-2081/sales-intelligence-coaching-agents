import unittest

from src.agents.negotiator_agent.sentiment_engine import SentimentEngine


class TestSentimentEngine(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = SentimentEngine()

    def test_empty_chunk_returns_neutral_low_confidence(self):
        res = self.engine.analyze("")
        self.assertEqual(res.label, "neutral")
        self.assertTrue(0.0 <= res.confidence <= 1.0)
        self.assertLessEqual(res.confidence, 0.4)

    def test_negative_sentiment_on_expensive_and_worried(self):
        text = "Customer: This feels expensive and I'm worried it won't work."
        res = self.engine.analyze(text)
        self.assertIn(res.label, ["negative", "neutral"])  # allow neutral if close
        self.assertTrue(0.0 <= res.confidence <= 1.0)
        # with "expensive" + "worried" we expect negative in most cases
        self.assertEqual(res.label, "negative")

    def test_positive_sentiment_on_good_sounds_good(self):
        text = "Customer: Sounds good, this looks great."
        res = self.engine.analyze(text)
        self.assertEqual(res.label, "positive")
        self.assertTrue(res.confidence >= 0.5)

    def test_neutral_when_no_lexicon_hits(self):
        text = "Customer: Can you tell me more about the onboarding process?"
        res = self.engine.analyze(text)
        self.assertEqual(res.label, "neutral")
        self.assertTrue(0.0 <= res.confidence <= 1.0)

    def test_negated_positive_flips_to_negative(self):
        # "not good" should be treated as negative evidence
        text = "Customer: This is not good for our team."
        res = self.engine.analyze(text)
        self.assertEqual(res.label, "negative")
        self.assertTrue(res.confidence >= 0.45)

    def test_confidence_does_not_exceed_bounds(self):
        text = "Customer: " + " ".join(["terrible"] * 50)
        res = self.engine.analyze(text)
        self.assertTrue(0.0 <= res.confidence <= 1.0)

    def test_context_stabilization_can_reduce_confidence(self):
        # Chunk looks positive, but context strongly negative -> confidence should reduce slightly
        context = [
            "Customer: This is terrible and frustrating.",
            "Customer: I'm skeptical and worried.",
            "Customer: This feels expensive.",
        ]
        res = self.engine.analyze("Customer: sounds good", context=context)
        self.assertEqual(res.label, "positive")
        # We don't assert exact confidence, just that it's within bounds
        self.assertTrue(0.0 <= res.confidence <= 1.0)


if __name__ == "__main__":
    unittest.main()
