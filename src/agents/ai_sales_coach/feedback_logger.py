#src/agents/ai_sales_coach/feedback_logger.py
from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional


@dataclass(frozen=True)
class FeedbackEvent:
    agent_name: str
    rep_id: str
    call_id: str
    tips_shown: List[str]
    action: str
    notes: Optional[str] = None
    edited_tip: Optional[str] = None
    timestamp_utc: Optional[str] = None

    def to_dict(self) -> dict:
        d = asdict(self)
        if not d.get("timestamp_utc"):
            d["timestamp_utc"] = datetime.now(timezone.utc).isoformat()
        return d


class FeedbackLogger:
    """
    Appends feedback events to a JSONL file.

    Default path:
      repo_root/mock-data/feedback/ai_sales_coach_feedback.jsonl
    """

    def __init__(self, log_path: Optional[str] = None) -> None:
        self._log_path = Path(log_path) if log_path else self._default_log_path()
        self._log_path.parent.mkdir(parents=True, exist_ok=True)

    def log(self, event: FeedbackEvent) -> None:
        record = event.to_dict()
        line = json.dumps(record, ensure_ascii=False)
        with self._log_path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")

    def _default_log_path(self) -> Path:
        repo_root = Path(__file__).resolve().parents[3]
        return repo_root / "mock-data" / "feedback" / "ai_sales_coach_feedback.jsonl"
