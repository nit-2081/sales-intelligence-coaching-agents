import unittest

from src.agents.negotiator_agent.llm_whisper_generator import LLMWhisperGenerator


class DummyClient:
    def __init__(self, output: str):
        self.output = output

    def generate(self, prompt: str) -> str:
        return self.output


class TestLLMWhisperGenerator(unittest.TestCase):
    def test_accepts_pure_json(self):
        client = DummyClient(
            '{"suggested_reply":"Totally fair — what outcome matters most?","tone":"curious","objection":"price","reason":"price concern"}'
        )
        gen = LLMWhisperGenerator(client=client)

        out = gen.generate(
            chunk_text="Customer: This is expensive.",
            context_window=["Customer: This is expensive."],
            sentiment_label="negative",
            objection="price",
            confidence=0.82,
        )
        self.assertEqual(out["tone"], "curious")
        self.assertEqual(out["objection"], "price")
        self.assertTrue(len(out["suggested_reply"]) > 5)

    def test_accepts_fenced_json(self):
        client = DummyClient(
            """```json
            {"suggested_reply":"That makes sense — what timeline are you aiming for?","tone":"curious","objection":"timing","reason":"timing hesitation"}
            ```"""
        )
        gen = LLMWhisperGenerator(client=client)

        out = gen.generate(
            chunk_text="Customer: Not now, maybe later.",
            context_window=["Customer: Not now, maybe later."],
            sentiment_label="neutral",
            objection="timing",
            confidence=0.70,
        )
        self.assertEqual(out["objection"], "timing")

    def test_rejects_missing_keys(self):
        client = DummyClient('{"suggested_reply":"Hi","tone":"calm","objection":"none"}')
        gen = LLMWhisperGenerator(client=client)

        with self.assertRaises(ValueError):
            gen.generate(
                chunk_text="Customer: ok",
                context_window=["Customer: ok"],
                sentiment_label="neutral",
                objection="none",
                confidence=0.65,
            )

    def test_rejects_auto_action_language(self):
        client = DummyClient(
            '{"suggested_reply":"I will email you the details now.","tone":"calm","objection":"none","reason":"follow up"}'
        )
        gen = LLMWhisperGenerator(client=client)

        with self.assertRaises(ValueError):
            gen.generate(
                chunk_text="Customer: ok",
                context_window=["Customer: ok"],
                sentiment_label="neutral",
                objection="none",
                confidence=0.90,
            )


if __name__ == "__main__":
    unittest.main()
