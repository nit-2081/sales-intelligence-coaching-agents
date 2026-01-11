from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Dict, Iterable, List, Optional, Tuple


@dataclass(frozen=True)
class RetentionSignals:
    """
    Signals extracted from a customer's usage history window.

    All percentages are in the range [0.0, 1.0] when present.
    Example: 0.65 means "65% drop".
    """
    window_days: int

    # Core trend signals
    login_drop_pct: Optional[float]
    active_minutes_drop_pct: Optional[float]
    feature_usage_drop_pct: Optional[float]

    # Risk pattern signals
    inactive_streak_days: int
    low_usage_days: int

    # Supporting stats (for reasons/debug)
    avg_logins_early: Optional[float]
    avg_logins_late: Optional[float]
    avg_minutes_early: Optional[float]
    avg_minutes_late: Optional[float]
    feature_rate_early: Optional[float]
    feature_rate_late: Optional[float]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "window_days": self.window_days,
            "login_drop_pct": self.login_drop_pct,
            "active_minutes_drop_pct": self.active_minutes_drop_pct,
            "feature_usage_drop_pct": self.feature_usage_drop_pct,
            "inactive_streak_days": self.inactive_streak_days,
            "low_usage_days": self.low_usage_days,
            "avg_logins_early": self.avg_logins_early,
            "avg_logins_late": self.avg_logins_late,
            "avg_minutes_early": self.avg_minutes_early,
            "avg_minutes_late": self.avg_minutes_late,
            "feature_rate_early": self.feature_rate_early,
            "feature_rate_late": self.feature_rate_late,
        }


class RetentionSignalExtractor:
    """
    Extracts churn-risk signals from a customer's usage window.

    Input expectation:
      - rows: list of dict-like records, sorted or unsorted.
      - each row should include:
          - date (string YYYY-MM-DD or datetime/date), optional but recommended
          - logins (int/float), optional
          - active_minutes (int/float), optional
          - key_feature_used (0/1, True/False), optional

    The extractor is tolerant to missing fields; missing metrics will yield None signals.
    """

    def __init__(
        self,
        date_key: str = "date",
        logins_key: str = "logins",
        minutes_key: str = "active_minutes",
        feature_key: str = "key_feature_used",
        low_usage_login_threshold: float = 1.0,
    ) -> None:
        self.date_key = date_key
        self.logins_key = logins_key
        self.minutes_key = minutes_key
        self.feature_key = feature_key
        self.low_usage_login_threshold = low_usage_login_threshold

    def extract(self, rows: List[Dict[str, Any]]) -> RetentionSignals:
        if not rows:
            # Empty window = strong risk pattern, but we keep drops as None.
            return RetentionSignals(
                window_days=0,
                login_drop_pct=None,
                active_minutes_drop_pct=None,
                feature_usage_drop_pct=None,
                inactive_streak_days=0,
                low_usage_days=0,
                avg_logins_early=None,
                avg_logins_late=None,
                avg_minutes_early=None,
                avg_minutes_late=None,
                feature_rate_early=None,
                feature_rate_late=None,
            )

        ordered = self._sort_rows_by_date(rows)

        # Split into early vs late halves (trend detection)
        early, late = self._split_halves(ordered)

        # Extract sequences
        logins_seq = self._num_seq(ordered, self.logins_key)
        minutes_seq = self._num_seq(ordered, self.minutes_key)
        feature_seq = self._bool_seq(ordered, self.feature_key)

        # Compute summary stats for halves
        avg_logins_early = self._avg(self._num_seq(early, self.logins_key))
        avg_logins_late = self._avg(self._num_seq(late, self.logins_key))

        avg_minutes_early = self._avg(self._num_seq(early, self.minutes_key))
        avg_minutes_late = self._avg(self._num_seq(late, self.minutes_key))

        feature_rate_early = self._rate_true(self._bool_seq(early, self.feature_key))
        feature_rate_late = self._rate_true(self._bool_seq(late, self.feature_key))

        # Compute drop percentages (early -> late)
        login_drop_pct = self._drop_pct(avg_logins_early, avg_logins_late)
        active_minutes_drop_pct = self._drop_pct(avg_minutes_early, avg_minutes_late)
        feature_usage_drop_pct = self._drop_pct(feature_rate_early, feature_rate_late)

        inactive_streak_days = self._inactive_streak_days(ordered)
        low_usage_days = self._low_usage_days(ordered)

        return RetentionSignals(
            window_days=len(ordered),
            login_drop_pct=login_drop_pct,
            active_minutes_drop_pct=active_minutes_drop_pct,
            feature_usage_drop_pct=feature_usage_drop_pct,
            inactive_streak_days=inactive_streak_days,
            low_usage_days=low_usage_days,
            avg_logins_early=avg_logins_early,
            avg_logins_late=avg_logins_late,
            avg_minutes_early=avg_minutes_early,
            avg_minutes_late=avg_minutes_late,
            feature_rate_early=feature_rate_early,
            feature_rate_late=feature_rate_late,
        )

    def _sort_rows_by_date(self, rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        # If date is missing or unparsable, keep original order.
        def key_fn(r: Dict[str, Any]) -> Tuple[int, Optional[date]]:
            raw = r.get(self.date_key)
            parsed = self._parse_date(raw)
            # push missing dates to the end but preserve relative order
            return (0 if parsed is not None else 1, parsed)

        try:
            return sorted(rows, key=key_fn)
        except Exception:
            return rows

    @staticmethod
    def _split_halves(rows: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        n = len(rows)
        if n <= 1:
            return rows, rows
        mid = n // 2
        early = rows[:mid]
        late = rows[mid:]
        return early, late

    @staticmethod
    def _parse_date(v: Any) -> Optional[date]:
        if v is None:
            return None
        if isinstance(v, date) and not isinstance(v, datetime):
            return v
        if isinstance(v, datetime):
            return v.date()
        if isinstance(v, str):
            # accept "YYYY-MM-DD"
            try:
                return datetime.strptime(v.strip(), "%Y-%m-%d").date()
            except Exception:
                return None
        return None

    @staticmethod
    def _to_float(v: Any) -> Optional[float]:
        if v is None:
            return None
        try:
            # handle strings like "12", "12.3"
            return float(v)
        except Exception:
            return None

    def _num_seq(self, rows: List[Dict[str, Any]], key: str) -> List[float]:
        out: List[float] = []
        for r in rows:
            fv = self._to_float(r.get(key))
            if fv is not None:
                out.append(fv)
        return out

    @staticmethod
    def _bool_seq(rows: List[Dict[str, Any]], key: str) -> List[bool]:
        out: List[bool] = []
        for r in rows:
            v = r.get(key)
            if v is None:
                continue
            if isinstance(v, bool):
                out.append(v)
            else:
                # accept 0/1, "0"/"1", "true"/"false"
                s = str(v).strip().lower()
                if s in {"1", "true", "yes", "y"}:
                    out.append(True)
                elif s in {"0", "false", "no", "n"}:
                    out.append(False)
        return out

    @staticmethod
    def _avg(seq: List[float]) -> Optional[float]:
        if not seq:
            return None
        return sum(seq) / float(len(seq))

    @staticmethod
    def _rate_true(seq: List[bool]) -> Optional[float]:
        if not seq:
            return None
        trues = sum(1 for x in seq if x)
        return trues / float(len(seq))

    @staticmethod
    def _drop_pct(early: Optional[float], late: Optional[float]) -> Optional[float]:
        """
        Returns drop percentage from early -> late:
          (early - late) / early, clamped to [0, 1] for drops.
        If late > early, drop becomes 0.0 (no drop).
        """
        if early is None or late is None:
            return None
        if early <= 0:
            return None
        raw = (early - late) / early
        if raw <= 0:
            return 0.0
        if raw >= 1:
            return 1.0
        return raw

    def _inactive_streak_days(self, ordered: List[Dict[str, Any]]) -> int:
        """
        Count consecutive trailing days where logins == 0 (or missing treated as 0).
        This is a common churn risk signal.
        """
        streak = 0
        # walk backwards (most recent to older)
        for r in reversed(ordered):
            v = self._to_float(r.get(self.logins_key))
            logins = 0.0 if v is None else v
            if logins <= 0.0:
                streak += 1
            else:
                break
        return streak

    def _low_usage_days(self, ordered: List[Dict[str, Any]]) -> int:
        """
        Count days in the window where logins are low (<= threshold).
        """
        count = 0
        for r in ordered:
            v = self._to_float(r.get(self.logins_key))
            logins = 0.0 if v is None else v
            if logins <= self.low_usage_login_threshold:
                count += 1
        return count
