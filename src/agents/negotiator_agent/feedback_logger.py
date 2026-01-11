from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass
class FeedbackEvent:
    agent: str
    ts_utc: str

    call_id: str
    chunk_id: int

    rep_action: str  # accepted | ignored | edited
    edited_text: Optional[str]

    objection: str
    sentiment_label: str

    confidence: float
    strength: str  # soft | strong
    generation_path: str  # llm | fallback

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent": self.agent,
            "ts_utc": self.ts_utc,
            "call_id": self.call_id,
            "chunk_id": self.chunk_id,
            "rep_action": self.rep_action,
            "edited_text": self.edited_text,
            "objection": self.objection,
            "sentiment_label": self.sentiment_label,
            "confidence": self.confidence,
            "strength": self.strength,
            "generation_path": self.generation_path,
        }


class FeedbackLogger:
    """
    JSONL feedback logger for Negotiator Agent.
    Stores what the rep did with each whisper.
    """

    def __init__(self, log_path: Optional[Path] = None) -> None:
        self.log_path = log_path or self._default_log_path()
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def log(
        self,
        *,
        call_id: str,
        chunk_id: int,
        rep_action: str,
        objection: str,
        sentiment_label: str,
        confidence: float,
        strength: str,
        generation_path: str,
        edited_text: Optional[str] = None,
    ) -> None:
        rep_action = (rep_action or "").strip().lower()
        if rep_action not in {"accepted", "ignored", "edited"}:
            raise ValueError("rep_action must be one of: accepted, ignored, edited")

        if rep_action != "edited":
            edited_text = None

        event = FeedbackEvent(
            agent="negotiator_agent",
            ts_utc=self.now_utc_iso(),
            call_id=str(call_id),
            chunk_id=int(chunk_id),
            rep_action=rep_action,
            edited_text=edited_text,
            objection=str(objection),
            sentiment_label=str(sentiment_label),
            confidence=float(confidence),
            strength=str(strength),
            generation_path=str(generation_path),
        )

        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event.to_dict(), ensure_ascii=False) + "\n")

    @staticmethod
    def now_utc_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    def _default_log_path(self) -> Path:
        # src/agents/negotiator_agent/feedback_logger.py -> repo root
        repo_root = Path(__file__).resolve().parents[3]
        return repo_root / "mock-data" / "feedback" / "negotiator_agent_feedback.jsonl"
