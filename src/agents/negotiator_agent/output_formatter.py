from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict, Optional

from src.agents.negotiator_agent.decision_engine import WhisperDecision


class OutputFormatter:
    """
    Formats the DecisionEngine output into a rep-facing whisper card.
    This is the Action Agent output (human-facing only).
    """

    def format(self, decision: WhisperDecision) -> Optional[Dict[str, Any]]:
        """
        Returns a dict suitable for UI/console display, or None if no whisper.
        """
        if not decision.should_whisper or not decision.suggested_reply:
            return None

        # Keep the card minimal and useful for reps
        card: Dict[str, Any] = {
            "call_id": decision.call_id,
            "chunk_id": decision.chunk_id,
            "whisper": {
                "suggested_reply": decision.suggested_reply,
                "tone": decision.tone,
                "objection": decision.objection,
            },
            "confidence": round(float(decision.confidence), 2),
            "strength": decision.strength,  # soft/strong
            "reason": decision.reason,
            "generation_path": decision.generation_path,  # llm/fallback
            "signals": {
                "sentiment_label": decision.sentiment_label,
                "sentiment_confidence": round(float(decision.sentiment_confidence), 2),
            },
            "debug": decision.debug,  # keep for evaluator visibility
        }

        return card
