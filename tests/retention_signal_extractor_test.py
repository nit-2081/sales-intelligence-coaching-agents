import unittest

from src.agents.retention_agent.signal_extractor import RetentionSignalExtractor


class TestRetentionSignalExtractor(unittest.TestCase):
    def setUp(self) -> None:
        self.ex = RetentionSignalExtractor()

    def test_empty_rows(self):
        sig = self.ex.extract([])
        self.assertEqual(sig.window_days, 0)
        self.assertIsNone(sig.login_drop_pct)
        self.assertEqual(sig.inactive_streak_days, 0)

    def test_drop_detected_between_halves(self):
        # Early half has higher usage than late half
        rows = [
            {"date": "2026-01-01", "logins": 10, "active_minutes": 100, "key_feature_used": 1},
            {"date": "2026-01-02", "logins": 8, "active_minutes": 90, "key_feature_used": 1},
            {"date": "2026-01-03", "logins": 3, "active_minutes": 30, "key_feature_used": 0},
            {"date": "2026-01-04", "logins": 2, "active_minutes": 20, "key_feature_used": 0},
        ]
        sig = self.ex.extract(rows)

        self.assertEqual(sig.window_days, 4)

        # Avg logins early = (10+8)/2 = 9
        # Avg logins late  = (3+2)/2 = 2.5
        # Drop pct = (9 - 2.5)/9 = 6.5/9 = 0.7222...
        self.assertIsNotNone(sig.login_drop_pct)
        self.assertAlmostEqual(sig.login_drop_pct, 6.5 / 9.0, places=4)

        # Feature early rate = 1.0, late rate = 0.0, drop = 1.0
        self.assertEqual(sig.feature_usage_drop_pct, 1.0)

    def test_inactive_streak_days_trailing_zeros(self):
        rows = [
            {"date": "2026-01-01", "logins": 2},
            {"date": "2026-01-02", "logins": 0},
            {"date": "2026-01-03", "logins": 0},
        ]
        sig = self.ex.extract(rows)
        self.assertEqual(sig.inactive_streak_days, 2)

    def test_sorting_by_date(self):
        # Provide out-of-order rows; extractor should sort by date
        rows = [
            {"date": "2026-01-03", "logins": 0, "active_minutes": 0, "key_feature_used": 0},
            {"date": "2026-01-01", "logins": 10, "active_minutes": 100, "key_feature_used": 1},
            {"date": "2026-01-02", "logins": 8, "active_minutes": 90, "key_feature_used": 1},
            {"date": "2026-01-04", "logins": 0, "active_minutes": 0, "key_feature_used": 0},
        ]
        sig = self.ex.extract(rows)

        # With last two days 0 logins, streak should be 2 (2026-01-03 and 2026-01-04)
        self.assertEqual(sig.inactive_streak_days, 2)

    def test_missing_fields_graceful(self):
        rows = [
            {"date": "2026-01-01"},
            {"date": "2026-01-02"},
            {"date": "2026-01-03"},
            {"date": "2026-01-04"},
        ]
        sig = self.ex.extract(rows)

        # No numeric data → drops are None, but it should not crash
        self.assertIsNone(sig.login_drop_pct)
        self.assertIsNone(sig.active_minutes_drop_pct)
        self.assertIsNone(sig.feature_usage_drop_pct)


if __name__ == "__main__":
    unittest.main()
