from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from src.agents.retention_agent.action_router import ActionDecision, RetentionAction
from src.agents.retention_agent.churn_model import ChurnAssessment
from src.agents.retention_agent.signal_extractor import RetentionSignals


@dataclass(frozen=True)
class CSMCard:
    customer_id: str
    latest_period: Optional[str]
    risk_band: str  # "low" | "medium" | "high"
    churn_score: float
    confidence: float
    reasons: List[str]
    recommended_action: str
    next_step_hint: str
    debug: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "customer_id": self.customer_id,
            "latest_period": self.latest_period,
            "risk_band": self.risk_band,
            "churn_score": self.churn_score,
            "confidence": self.confidence,
            "reasons": self.reasons,
            "recommended_action": self.recommended_action,
            "next_step_hint": self.next_step_hint,
            "debug": self.debug,
        }


class OutputFormatter:
    """
    Formats retention decisions into a clean, human-facing 'CSM card' structure.
    """

    def format_card(
        self,
        customer_id: str,
        latest_period: Optional[str],
        signals: RetentionSignals,
        assessment: ChurnAssessment,
        action: ActionDecision,
    ) -> CSMCard:
        risk_band = self._risk_band(assessment.churn_score, action.action)
        next_step = self._next_step_hint(action.action, assessment.churn_score)

        debug = {
            "risk_points": assessment.risk_points,
            "signals": signals.to_dict(),
            "thresholds": action.thresholds,
        }

        return CSMCard(
            customer_id=customer_id,
            latest_period=latest_period,
            risk_band=risk_band,
            churn_score=assessment.churn_score,
            confidence=assessment.confidence,
            reasons=assessment.reasons,
            recommended_action=action.action.value,
            next_step_hint=next_step,
            debug=debug,
        )

    @staticmethod
    def _risk_band(churn_score: float, action: RetentionAction) -> str:
        # Use action as the source of truth (rules decide)
        if action == RetentionAction.DRAFT_REENGAGEMENT:
            return "high"
        if action == RetentionAction.ALERT_CSM:
            return "medium"
        return "low"

    @staticmethod
    def _next_step_hint(action: RetentionAction, churn_score: float) -> str:
        if action == RetentionAction.DRAFT_REENGAGEMENT:
            return "Review the draft message and (if appropriate) reach out to the customer with help/resources."
        if action == RetentionAction.ALERT_CSM:
            return "Review usage trends and decide whether a check-in call or email is needed."
        return "No action needed. Continue monitoring in the next batch."
