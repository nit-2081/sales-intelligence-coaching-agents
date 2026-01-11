import unittest

from src.agents.retention_agent.action_router import ActionDecision, RetentionAction
from src.agents.retention_agent.churn_model import ChurnAssessment
from src.agents.retention_agent.output_formatter import OutputFormatter
from src.agents.retention_agent.signal_extractor import RetentionSignals


class TestOutputFormatter(unittest.TestCase):
    def test_format_card(self):
        fmt = OutputFormatter()

        signals = RetentionSignals(
            window_days=4,
            login_drop_pct=0.7,
            active_minutes_drop_pct=0.6,
            feature_usage_drop_pct=0.5,
            inactive_streak_days=2,
            low_usage_days=3,
            avg_logins_early=10, avg_logins_late=3,
            avg_minutes_early=100, avg_minutes_late=40,
            feature_rate_early=5, feature_rate_late=2,
        )

        assessment = ChurnAssessment(
            churn_score=0.91,
            confidence=0.85,
            reasons=["Logins dropped ~70%."],
            risk_points=60.0,
        )

        action = ActionDecision(
            action=RetentionAction.DRAFT_REENGAGEMENT,
            reason="High churn risk.",
            thresholds={"high_threshold": 0.8, "medium_threshold": 0.5, "min_confidence_for_high": 0.6},
        )

        card = fmt.format_card(
            customer_id="CUST_003",
            latest_period="Week_4",
            signals=signals,
            assessment=assessment,
            action=action,
        )

        d = card.to_dict()
        self.assertEqual(d["risk_band"], "high")
        self.assertEqual(d["recommended_action"], "draft_reengagement")
        self.assertTrue(len(d["reasons"]) >= 1)


if __name__ == "__main__":
    unittest.main()
