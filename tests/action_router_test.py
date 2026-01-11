import unittest

from src.agents.retention_agent.action_router import ActionRouter, RetentionAction


class TestActionRouter(unittest.TestCase):
    def setUp(self) -> None:
        self.router = ActionRouter(high_threshold=0.80, medium_threshold=0.50, min_confidence_for_high=0.60)

    def test_high_risk_requires_confidence(self):
        # High score but low confidence -> should fall back to ALERT_CSM (medium path)
        d = self.router.route(churn_score=0.90, confidence=0.20)
        self.assertEqual(d.action, RetentionAction.ALERT_CSM)

        # High score + enough confidence -> draft re-engagement
        d2 = self.router.route(churn_score=0.90, confidence=0.80)
        self.assertEqual(d2.action, RetentionAction.DRAFT_REENGAGEMENT)

    def test_medium_risk_alert(self):
        d = self.router.route(churn_score=0.60, confidence=0.10)
        self.assertEqual(d.action, RetentionAction.ALERT_CSM)

    def test_low_risk_no_action(self):
        d = self.router.route(churn_score=0.10, confidence=0.90)
        self.assertEqual(d.action, RetentionAction.NO_ACTION)


if __name__ == "__main__":
    unittest.main()
