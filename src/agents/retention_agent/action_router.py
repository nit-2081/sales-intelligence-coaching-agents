from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional


class RetentionAction(str, Enum):
    NO_ACTION = "no_action"
    ALERT_CSM = "alert_csm"
    DRAFT_REENGAGEMENT = "draft_reengagement"


@dataclass(frozen=True)
class ActionDecision:
    action: RetentionAction
    reason: str
    thresholds: Dict[str, float]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action": self.action.value,
            "reason": self.reason,
            "thresholds": self.thresholds,
        }


class ActionRouter:
    """
    Routes churn scores into safe human-facing actions.

    Rules:
      - High risk: churn_score >= high_threshold AND confidence >= min_confidence_for_auto_suggest
          -> DRAFT_REENGAGEMENT (still human-reviewed; no auto-send)
      - Medium: churn_score >= medium_threshold
          -> ALERT_CSM
      - Else:
          -> NO_ACTION
    """

    def __init__(
        self,
        high_threshold: float = 0.80,
        medium_threshold: float = 0.50,
        min_confidence_for_high: float = 0.60,
    ) -> None:
        self.high_threshold = high_threshold
        self.medium_threshold = medium_threshold
        self.min_confidence_for_high = min_confidence_for_high

    def route(self, churn_score: float, confidence: float) -> ActionDecision:
        churn_score = self._clamp01(churn_score)
        confidence = self._clamp01(confidence)

        thresholds = {
            "high_threshold": self.high_threshold,
            "medium_threshold": self.medium_threshold,
            "min_confidence_for_high": self.min_confidence_for_high,
        }

        # High risk
        if churn_score >= self.high_threshold and confidence >= self.min_confidence_for_high:
            return ActionDecision(
                action=RetentionAction.DRAFT_REENGAGEMENT,
                reason=f"High churn risk (score {churn_score:.2f}) with sufficient confidence ({confidence:.2f}).",
                thresholds=thresholds,
            )

        # Medium risk
        if churn_score >= self.medium_threshold:
            return ActionDecision(
                action=RetentionAction.ALERT_CSM,
                reason=f"Medium churn risk (score {churn_score:.2f}); recommend CSM review.",
                thresholds=thresholds,
            )

        # Low risk
        return ActionDecision(
            action=RetentionAction.NO_ACTION,
            reason=f"Low churn risk (score {churn_score:.2f}); no action recommended.",
            thresholds=thresholds,
        )

    @staticmethod
    def _clamp01(x: float) -> float:
        if x < 0.0:
            return 0.0
        if x > 1.0:
            return 1.0
        return x
