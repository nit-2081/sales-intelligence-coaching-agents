import unittest

from src.agents.negotiator_agent.decision_engine import DecisionEngine
from src.agents.negotiator_agent.fallback_templates import FallbackTemplateGenerator
from src.agents.negotiator_agent.objection_detector import Objection
from src.agents.negotiator_agent.sentiment_engine import SentimentResult


class DummyLLMGood:
    def generate(self, **kwargs):
        return {
            "suggested_reply": "Totally fair — can I ask what outcome matters most so I can map value to that?",
            "tone": "curious",
            "objection": kwargs.get("objection", "none"),
            "reason": "llm_ok"
        }


class DummyLLMBadJSON:
    def generate(self, **kwargs):
        return "not a dict"


class DummyLLMRaises:
    def generate(self, **kwargs):
        raise RuntimeError("boom")


class TestDecisionEngine(unittest.TestCase):
    def setUp(self) -> None:
        self.fallback = FallbackTemplateGenerator()

    def test_no_trigger_no_whisper(self):
        engine = DecisionEngine(llm_generator=DummyLLMGood(), fallback_generator=self.fallback)
        sentiment = SentimentResult(label="neutral", confidence=0.5, score=0.0, reasons=["no_lexicon_hits"])
        decision = engine.decide(
            call_id="c1",
            chunk_id=1,
            chunk_text="Customer: Can you explain onboarding?",
            context_window=["Customer: Can you explain onboarding?"],
            sentiment=sentiment,
            objections=[],
        )
        self.assertFalse(decision.should_whisper)
        self.assertEqual(decision.generation_path, "none")

    def test_objection_triggers_llm_path_when_valid(self):
        engine = DecisionEngine(llm_generator=DummyLLMGood(), fallback_generator=self.fallback)
        sentiment = SentimentResult(label="neutral", confidence=0.5, score=0.0, reasons=["no_lexicon_hits"])
        objections = [Objection(label="price", evidence=["expensive_word", "budget_word"])]
        decision = engine.decide(
            call_id="c1",
            chunk_id=1,
            chunk_text="Customer: This is expensive for our budget.",
            context_window=["Customer: This is expensive for our budget."],
            sentiment=sentiment,
            objections=objections,
        )
        self.assertTrue(decision.should_whisper)
        self.assertEqual(decision.generation_path, "llm")
        self.assertIn(decision.strength, ["soft", "strong"])
        self.assertTrue(0.0 <= decision.confidence <= 1.0)

    def test_llm_invalid_output_falls_back(self):
        engine = DecisionEngine(llm_generator=DummyLLMBadJSON(), fallback_generator=self.fallback)
        sentiment = SentimentResult(label="neutral", confidence=0.5, score=0.0, reasons=["no_lexicon_hits"])
        objections = [Objection(label="timing", evidence=["not_now_phrase"])]
        decision = engine.decide(
            call_id="c1",
            chunk_id=2,
            chunk_text="Customer: Not now, maybe later.",
            context_window=["Customer: Not now, maybe later."],
            sentiment=sentiment,
            objections=objections,
        )
        self.assertTrue(decision.should_whisper)
        self.assertEqual(decision.generation_path, "fallback")

    def test_llm_exception_falls_back(self):
        engine = DecisionEngine(llm_generator=DummyLLMRaises(), fallback_generator=self.fallback)
        sentiment = SentimentResult(label="negative", confidence=0.85, score=-2.0, reasons=["neg_word:worried"])
        objections = [Objection(label="trust", evidence=["skeptical_word"])]
        decision = engine.decide(
            call_id="c2",
            chunk_id=1,
            chunk_text="Customer: I'm skeptical and worried this won't work.",
            context_window=["Customer: I'm skeptical and worried this won't work."],
            sentiment=sentiment,
            objections=objections,
        )
        self.assertTrue(decision.should_whisper)
        self.assertEqual(decision.generation_path, "fallback")

    def test_low_confidence_suppresses_whisper(self):
        engine = DecisionEngine(
            llm_generator=DummyLLMGood(),
            fallback_generator=self.fallback,
            min_soft_confidence=0.95,  # artificially high
        )
        sentiment = SentimentResult(label="negative", confidence=0.70, score=-1.0, reasons=["neg_word:worried"])
        objections = []  # only negative sentiment trigger
        decision = engine.decide(
            call_id="c3",
            chunk_id=1,
            chunk_text="Customer: I'm worried.",
            context_window=["Customer: I'm worried."],
            sentiment=sentiment,
            objections=objections,
        )
        self.assertFalse(decision.should_whisper)
        self.assertEqual(decision.generation_path, "none")


if __name__ == "__main__":
    unittest.main()
