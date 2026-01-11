from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

# Reuse your shared LLM client (already exists in your repo)
from src.shared.llm.gemini_langchain_client import GeminiLangChainClient, GeminiLangChainConfig


@dataclass
class WhisperLLMResult:
    suggested_reply: str
    tone: str
    objection: str
    reason: str

    def to_dict(self) -> Dict[str, str]:
        return {
            "suggested_reply": self.suggested_reply,
            "tone": self.tone,
            "objection": self.objection,
            "reason": self.reason,
        }


class LLMWhisperGenerator:
    """
    LLM-based whisper generator (PRIMARY path).
    Must return a dict with keys:
      - suggested_reply (1–2 lines)
      - tone (calm|curious|reassuring|firm)
      - objection (price|timing|competitor|trust|none)
      - reason (short)
    If anything goes wrong, raise an exception -> DecisionEngine fallback triggers.
    """

    ALLOWED_TONES = {"calm", "curious", "reassuring", "firm"}
    ALLOWED_OBJECTIONS = {"price", "timing", "competitor", "trust", "none"}

    def __init__(self, client: Optional[GeminiLangChainClient] = None) -> None:
        # Allow injection for tests
        self.client = client or GeminiLangChainClient(GeminiLangChainConfig())

    def generate(
        self,
        *,
        chunk_text: str,
        context_window: List[str],
        sentiment_label: str,
        objection: str,
        confidence: float,
    ) -> Dict[str, str]:
        prompt = self._build_prompt(
            chunk_text=chunk_text,
            context_window=context_window,
            sentiment_label=sentiment_label,
            objection=objection,
            confidence=confidence,
        )

        try:
            raw = self.client.generate_raw(prompt)
            data = self._extract_json(raw)
            result = self._validate_and_normalize(data)
            return result.to_dict()

        except Exception as e:
            # Optional: keep the detailed error only in logs, not in UI fields.
            # print(f"[LLM ERROR] {type(e).__name__}: {e}")  # or your logger

            # IMPORTANT: do NOT raise with f"...{e}" because upstream will display it.
            raise RuntimeError("LLM_UNAVAILABLE") from None

    def _build_prompt(
        self,
        *,
        chunk_text: str,
        context_window: List[str],
        sentiment_label: str,
        objection: str,
        confidence: float,
    ) -> str:
        ctx = "\n".join(context_window[-5:]) if context_window else ""

        # Hard constraints:
        # - rep-facing only
        # - do not promise discounts
        # - do not claim you already did something (no auto-actions)
        # - keep reply 1–2 lines
        return f"""
You are a Negotiator Agent that provides whisper coaching to a human sales rep DURING a call.
You never speak to the customer. You only suggest what the rep could say next.

CONTEXT (last turns):
{ctx}

CURRENT CHUNK:
{chunk_text}

DETECTED SIGNALS:
- sentiment_label: {sentiment_label}
- objection: {objection}
- decision_confidence: {confidence:.2f}

RULES:
- Output MUST be valid JSON only (no markdown, no extra text).
- suggested_reply MUST be 1–2 lines, <= 280 chars.
- No promises/guarantees. No discounts unless customer explicitly asked for discount.
- No automated actions (don't say you'll email/send/trigger anything).
- Keep tone aligned with sentiment.

Return EXACTLY this JSON schema:
{{
  "suggested_reply": "string",
  "tone": "calm|curious|reassuring|firm",
  "objection": "price|timing|competitor|trust|none",
  "reason": "short justification"
}}
""".strip()

    def _extract_json(self, raw: str) -> Dict[str, Any]:
        """
        Extract JSON from model output.
        Accepts:
        - pure JSON
        - fenced ```json ... ```
        """
        if raw is None:
            raise ValueError("LLM returned None")

        text = str(raw).strip()

        # If it's already JSON
        if text.startswith("{") and text.endswith("}"):
            return json.loads(text)

        # Extract fenced block
        fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.DOTALL | re.IGNORECASE)
        if fence:
            return json.loads(fence.group(1).strip())

        # As a last attempt, find first {...} block
        brace = re.search(r"(\{.*\})", text, flags=re.DOTALL)
        if brace:
            return json.loads(brace.group(1).strip())

        raise ValueError("LLM output did not contain JSON")

    def _validate_and_normalize(self, data: Dict[str, Any]) -> WhisperLLMResult:
        if not isinstance(data, dict):
            raise ValueError("LLM JSON is not an object")

        for k in ["suggested_reply", "tone", "objection", "reason"]:
            if k not in data:
                raise ValueError(f"Missing key: {k}")

        suggested = str(data["suggested_reply"]).strip()
        tone = str(data["tone"]).strip().lower()
        objection = str(data["objection"]).strip().lower()
        reason = str(data["reason"]).strip()

        # Constraints
        if not suggested:
            raise ValueError("Empty suggested_reply")
        if suggested.count("\n") > 1:
            raise ValueError("suggested_reply must be 1–2 lines max")
        if len(suggested) > 280:
            raise ValueError("suggested_reply too long")

        if tone not in self.ALLOWED_TONES:
            raise ValueError(f"Invalid tone: {tone}")

        if objection not in self.ALLOWED_OBJECTIONS:
            # normalize unknown into "none" (still safe)
            objection = "none"

        # Safety: ban auto-actions
        low = suggested.lower()
        banned = ["i will email", "i'll email", "i will send", "sending you", "i’ll send", "auto-send"]
        if any(b in low for b in banned):
            raise ValueError("Auto-action language detected")

        return WhisperLLMResult(
            suggested_reply=suggested,
            tone=tone,
            objection=objection,
            reason=reason or "llm_generated",
        )
