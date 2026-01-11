import unittest

from src.agents.negotiator_agent.objection_detector import ObjectionDetector


class TestObjectionDetector(unittest.TestCase):
    def setUp(self) -> None:
        self.detector = ObjectionDetector()

    def test_empty_text_returns_no_objections(self):
        obs = self.detector.detect("")
        self.assertEqual(obs, [])

    def test_detects_price_objection(self):
        text = "Customer: This feels expensive and our budget is tight."
        obs = self.detector.detect(text)
        labels = [o.label for o in obs]
        self.assertIn("price", labels)

    def test_detects_timing_objection(self):
        text = "Customer: Not now, we're busy this quarter. Maybe later."
        obs = self.detector.detect(text)
        labels = [o.label for o in obs]
        self.assertIn("timing", labels)

    def test_detects_competitor_objection(self):
        text = "Customer: We are currently using CompetitorX. Why should we switch?"
        obs = self.detector.detect(text)
        labels = [o.label for o in obs]
        self.assertIn("competitor", labels)

    def test_detects_trust_objection(self):
        text = "Customer: I'm skeptical. We have been burned before and support was terrible."
        obs = self.detector.detect(text)
        labels = [o.label for o in obs]
        self.assertIn("trust", labels)

    def test_priority_trust_over_price(self):
        text = "Customer: I'm skeptical and this feels expensive."
        obs = self.detector.detect(text)
        self.assertTrue(len(obs) >= 2)
        self.assertEqual(obs[0].label, "trust")  # trust must be first
        self.assertIn("price", [o.label for o in obs])

    def test_primary_objection_none(self):
        self.assertEqual(self.detector.primary_objection([]), "none")


if __name__ == "__main__":
    unittest.main()
