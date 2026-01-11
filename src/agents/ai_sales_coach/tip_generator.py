#src/agents/ai_sales_coach/tip_generator.py
from __future__ import annotations

import json
import os
from typing import Dict, Any, List

from src.shared.llm.gemini_langchain_client import GeminiLangChainClient


PROMPT_PATH = os.path.join(
    os.path.dirname(__file__),
    "..", "..", "shared", "prompts", "ai_sales_coach_tips.txt"
)


def _load_prompt() -> str:
    with open(PROMPT_PATH, "r", encoding="utf-8") as f:
        return f.read()


def _safe_fallback_tips(top_gaps: List[str]) -> List[str]:
    base = [
        "Acknowledge the customer’s concern first before presenting a solution.",
        "When objections come up, ask one clarifying question before responding.",
        "End with a clear recap and confirm the next step with a date/time.",
    ]
    if top_gaps:
        g = top_gaps[0].lower()
        if "empathy" in g:
            base[0] = "Start by reflecting the customer’s concern in one sentence before pitching value."
        elif "objection" in g:
            base[1] = "Handle objections by confirming the concern, asking one question, then tying back to outcomes."
        elif "closing" in g or "next step" in g:
            base[2] = "Close with one clear next step and ask for explicit confirmation (yes/no)."

    return base[:3]


def _extract_json(raw: str) -> Dict[str, Any]:
    """
    Gemini sometimes returns extra text around JSON.
    This tries:
    1) direct json.loads
    2) extract first {...} block and parse
    """
    raw = (raw or "").strip()

    try:
        return json.loads(raw)
    except Exception:
        pass

    start = raw.find("{")
    end = raw.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = raw[start : end + 1]
        return json.loads(candidate)

    raise ValueError("Could not parse JSON from LLM output")


def generate_tips(performance_summary: Dict[str, Any], top_gaps: List[str]) -> List[str]:
    """
    Returns exactly 3 tips.
    Uses Gemini (LangChain) when available, otherwise falls back to templates.

    performance_summary: dict produced from scoring/gaps (signals, scores, gaps)
    top_gaps: list of strings like ["empathy", "objection_handling"]
    """
    prompt_template = _load_prompt()
    variables = {
        "performance_summary": json.dumps(performance_summary, ensure_ascii=False),
        "top_gaps": ", ".join(top_gaps),
        "confidence": str(performance_summary.get("confidence", 0.0)),
    }



    try:
        client = GeminiLangChainClient()
        raw = client.generate(prompt_template, variables)
        print("[DEBUG] Raw LLM output for tips:", raw)
        data = _extract_json(raw)
        tips = data.get("tips", [])

        if not isinstance(tips, list):
            raise ValueError("LLM returned non-list tips")

        tips = [str(t).strip() for t in tips if str(t).strip()]
        if len(tips) < 3:
            raise ValueError(f"LLM returned {len(tips)} tips instead of 3")

        return tips

    except Exception as e:
        print("LLM FAILED, USING FALLBACK:", str(e))
        return _safe_fallback_tips(top_gaps)
