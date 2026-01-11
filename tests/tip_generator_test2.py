import json

def main():
    print("TEST START")

    # ---- MOCK Gemini client so no API calls happen ----
    import src.shared.llm.gemini_langchain_client as llm_mod

    class FakeClient:
        def generate(self, prompt_template, variables):
            print("FAKE GEMINI CALLED")
            # Show what we passed in (optional)
            perf = variables.get("performance_summary", "")
            print("performance_summary:", perf[:120], "..." if len(perf) > 120 else "")
            return json.dumps({"tips": ["tip1", "tip2", "tip3"]})

    llm_mod.GeminiLangChainClient = lambda *args, **kwargs: FakeClient()

    # ---- Call tip generator ----
    from src.agents.ai_sales_coach.tip_generator import generate_tips

    performance_summary = {
        "call_id": "call_01",
        "scores": {"overall": 65},
        "signals": {"empathy_hits": 1, "objections": ["price"], "closing_attempted": False},
        "top_gaps": ["empathy", "objection_handling"]
    }

    tips = generate_tips(performance_summary=performance_summary, top_gaps=["empathy"])
    print("TIPS:", tips)

    assert tips == ["tip1", "tip2", "tip3"]
    print("TEST PASS ✅")


if __name__ == "__main__":
    main()
