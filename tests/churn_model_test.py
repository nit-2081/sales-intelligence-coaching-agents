import unittest

from src.agents.retention_agent.churn_model import ChurnModel
from src.agents.retention_agent.signal_extractor import RetentionSignals


class TestChurnModel(unittest.TestCase):
    def setUp(self) -> None:
        self.model = ChurnModel()

    def test_higher_drop_gives_higher_score(self):
        low_risk = RetentionSignals(
            window_days=4,
            login_drop_pct=0.10,
            active_minutes_drop_pct=0.10,
            feature_usage_drop_pct=0.10,
            inactive_streak_days=0,
            low_usage_days=0,
            avg_logins_early=10, avg_logins_late=9,
            avg_minutes_early=100, avg_minutes_late=90,
            feature_rate_early=1.0, feature_rate_late=0.9,
        )
        high_risk = RetentionSignals(
            window_days=4,
            login_drop_pct=0.70,
            active_minutes_drop_pct=0.60,
            feature_usage_drop_pct=0.80,
            inactive_streak_days=2,
            low_usage_days=3,
            avg_logins_early=10, avg_logins_late=3,
            avg_minutes_early=100, avg_minutes_late=40,
            feature_rate_early=1.0, feature_rate_late=0.2,
        )

        a1 = self.model.score(low_risk)
        a2 = self.model.score(high_risk)

        self.assertLess(a1.churn_score, a2.churn_score)
        self.assertGreater(a2.risk_points, a1.risk_points)
        self.assertTrue(len(a2.reasons) >= 1)

    def test_missing_optional_signals_still_scores(self):
        sig = RetentionSignals(
            window_days=4,
            login_drop_pct=0.60,
            active_minutes_drop_pct=None,
            feature_usage_drop_pct=None,
            inactive_streak_days=2,
            low_usage_days=3,
            avg_logins_early=10, avg_logins_late=4,
            avg_minutes_early=None, avg_minutes_late=None,
            feature_rate_early=None, feature_rate_late=None,
        )
        a = self.model.score(sig)
        self.assertGreaterEqual(a.churn_score, 0.0)
        self.assertLessEqual(a.churn_score, 1.0)
        self.assertGreaterEqual(a.confidence, 0.0)
        self.assertLessEqual(a.confidence, 1.0)

    def test_no_strong_signals_reason(self):
        sig = RetentionSignals(
            window_days=4,
            login_drop_pct=0.0,
            active_minutes_drop_pct=0.0,
            feature_usage_drop_pct=0.0,
            inactive_streak_days=0,
            low_usage_days=0,
            avg_logins_early=10, avg_logins_late=10,
            avg_minutes_early=100, avg_minutes_late=100,
            feature_rate_early=1.0, feature_rate_late=1.0,
        )
        a = self.model.score(sig)
        self.assertTrue(len(a.reasons) >= 1)


if __name__ == "__main__":
    unittest.main()
