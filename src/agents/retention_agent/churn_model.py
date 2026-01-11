from __future__ import annotations

from dataclasses import dataclass
from math import exp
from typing import Any, Dict, List, Optional

from src.agents.retention_agent.signal_extractor import RetentionSignals


@dataclass(frozen=True)
class ChurnAssessment:
    """
    Output of churn scoring.

    churn_score: probability-like number in [0, 1]
    confidence: reliability estimate in [0, 1]
    reasons: short human-readable bullets (top drivers)
    risk_points: internal explainable score in [0, 100]
    """
    churn_score: float
    confidence: float
    reasons: List[str]
    risk_points: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "churn_score": self.churn_score,
            "confidence": self.confidence,
            "reasons": self.reasons,
            "risk_points": self.risk_points,
        }


class ChurnModel:
    """
    ML-lite churn model (explainable + deterministic).

    Approach:
      - Convert signals into "risk points" (0..100)
      - Convert risk points into churn_score (0..1) via a sigmoid
      - Compute confidence based on signal availability and window length

    NOTE:
      - This is intentionally transparent for evaluation.
      - We can swap to sklearn LogisticRegression later if needed.
    """

    def __init__(
        self,
        # Weighting (points) for the main drivers:
        w_login_drop: float = 35.0,
        w_minutes_drop: float = 20.0,
        w_feature_drop: float = 15.0,
        w_inactive_streak: float = 20.0,
        w_low_usage_days: float = 10.0,
        # Sigmoid calibration:
        sigmoid_center: float = 28.0,
        sigmoid_scale: float = 10.0,
    ) -> None:
        self.w_login_drop = w_login_drop
        self.w_minutes_drop = w_minutes_drop
        self.w_feature_drop = w_feature_drop
        self.w_inactive_streak = w_inactive_streak
        self.w_low_usage_days = w_low_usage_days

        self.sigmoid_center = sigmoid_center
        self.sigmoid_scale = sigmoid_scale

    def score(self, signals: RetentionSignals) -> ChurnAssessment:
        points = 0.0
        reasons: List[str] = []

        # --- 1) Drops (0..1) => scaled into points
        # login drop
        if signals.login_drop_pct is not None:
            ld = self._clamp01(signals.login_drop_pct)
            points += self.w_login_drop * ld
            if ld >= 0.50:
                reasons.append(f"Logins dropped ~{int(ld * 100)}% (early vs late).")

        # active minutes drop (optional depending on schema)
        if signals.active_minutes_drop_pct is not None:
            md = self._clamp01(signals.active_minutes_drop_pct)
            points += self.w_minutes_drop * md
            if md >= 0.50:
                reasons.append(f"Engagement time dropped ~{int(md * 100)}% (early vs late).")

        # feature usage drop (optional)
        if signals.feature_usage_drop_pct is not None:
            fd = self._clamp01(signals.feature_usage_drop_pct)
            points += self.w_feature_drop * fd
            if fd >= 0.50:
                reasons.append(f"Feature usage dropped ~{int(fd * 100)}% (early vs late).")

        # --- 2) Inactivity streak (integer)
        # We cap impact after 7 to avoid infinite growth
        if signals.window_days > 0:
            streak = max(0, int(signals.inactive_streak_days))
            streak_norm = self._clamp01(streak / 7.0)
            points += self.w_inactive_streak * streak_norm
            if streak >= 2:
                reasons.append(f"Inactive streak: {streak} consecutive periods with 0 logins.")

        # --- 3) Low usage days (integer)
        if signals.window_days > 0:
            low = max(0, int(signals.low_usage_days))
            low_norm = self._clamp01(low / max(1, signals.window_days))
            points += self.w_low_usage_days * low_norm
            if low_norm >= 0.60 and signals.window_days >= 3:
                reasons.append(f"Low usage in {low}/{signals.window_days} periods.")

        # Clamp risk points
        risk_points = self._clamp(points, 0.0, 100.0)

        # Convert to churn_score via sigmoid
        churn_score = self._sigmoid(risk_points, center=self.sigmoid_center, scale=self.sigmoid_scale)

        # Confidence: based on how many key signals exist + window size
        confidence = self._confidence(signals)

        # If we have no reasons (e.g., mild patterns), provide a safe generic reason
        if not reasons:
            reasons = ["No strong churn signals detected; continue monitoring usage trends."]

        # Keep reasons short and limited
        reasons = reasons[:3]

        return ChurnAssessment(
            churn_score=churn_score,
            confidence=confidence,
            reasons=reasons,
            risk_points=risk_points,
        )

    # -----------------------
    # Internals
    # -----------------------

    @staticmethod
    def _clamp(x: float, lo: float, hi: float) -> float:
        if x < lo:
            return lo
        if x > hi:
            return hi
        return x

    @staticmethod
    def _clamp01(x: float) -> float:
        return ChurnModel._clamp(x, 0.0, 1.0)

    @staticmethod
    def _sigmoid(points: float, center: float, scale: float) -> float:
        """
        Sigmoid mapping:
          score = 1 / (1 + exp(-(points - center)/scale))
        """
        # protect against scale=0
        s = scale if scale != 0 else 1.0
        z = (points - center) / s
        return 1.0 / (1.0 + exp(-z))

    def _confidence(self, signals: RetentionSignals) -> float:
        """
        Confidence is higher when:
          - we have more available numeric signals
          - the window length is reasonable
        """
        available = 0
        total = 3  # drop signals we care about: login/minutes/feature

        if signals.login_drop_pct is not None:
            available += 1
        if signals.active_minutes_drop_pct is not None:
            available += 1
        if signals.feature_usage_drop_pct is not None:
            available += 1

        # base from availability
        base = available / float(total)  # 0..1

        # add window contribution (0..1) where >=4 is good for weekly demo
        w = signals.window_days
        window_factor = self._clamp01(w / 4.0)  # 0->0, 4->1, >4 capped

        # inactivity/low_usage are always computable if window_days>0, but still weak if tiny window
        confidence = 0.20 + (0.55 * base) + (0.25 * window_factor)

        return self._clamp(confidence, 0.0, 1.0)
