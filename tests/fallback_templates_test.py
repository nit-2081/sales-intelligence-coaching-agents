import unittest

from src.agents.negotiator_agent.fallback_templates import FallbackTemplateGenerator


class TestFallbackTemplateGenerator(unittest.TestCase):
    def setUp(self) -> None:
        self.gen = FallbackTemplateGenerator()

    def test_generates_price_template(self):
        w = self.gen.generate("price")
        self.assertEqual(w.objection, "price")
        self.assertTrue(len(w.suggested_reply) > 10)

    def test_unknown_objection_defaults_to_none(self):
        w = self.gen.generate("random_objection_type")
        self.assertEqual(w.objection, "none")

    def test_reason_is_propagated(self):
        w = self.gen.generate("timing", reason="llm_failed")
        self.assertEqual(w.reason, "llm_failed")


if __name__ == "__main__":
    unittest.main()
