from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class FeedbackEvent:
    """
    One feedback event for retention outputs.

    action_taken:
      - accepted: CSM acted on the recommendation
      - ignored: CSM dismissed it
      - edited: CSM modified draft/action before acting
    """
    timestamp_utc: str
    customer_id: str
    recommended_action: str
    action_taken: str  # "accepted" | "ignored" | "edited"
    notes: Optional[str] = None
    churn_score: Optional[float] = None
    confidence: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp_utc": self.timestamp_utc,
            "customer_id": self.customer_id,
            "recommended_action": self.recommended_action,
            "action_taken": self.action_taken,
            "notes": self.notes,
            "churn_score": self.churn_score,
            "confidence": self.confidence,
        }


class FeedbackLogger:
    """
    Writes feedback events to a JSONL file (one JSON object per line).
    """

    def __init__(self, log_path: Optional[Path] = None) -> None:
        self.log_path = log_path or self._default_log_path()
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def log(self, event: FeedbackEvent) -> None:
        line = json.dumps(event.to_dict(), ensure_ascii=False)
        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")

    @staticmethod
    def now_utc_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _default_log_path() -> Path:
        repo_root = Path(__file__).resolve().parents[3]
        return repo_root / "mock-data" / "feedback" / "retention_agent_feedback.jsonl"
