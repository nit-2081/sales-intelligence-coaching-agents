# src/agents/ai_sales_coach/scoring_engine.py

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Dict, List, Tuple, Optional

from src.agents.ai_sales_coach.signal_extractor import CoachSignals
from src.shared.ml.coach_quality_model import CoachQualityModel


@dataclass(frozen=True)
class CoachScores:
    empathy: int
    pacing: int
    objection_handling: int
    closing: int

    def to_dict(self) -> Dict[str, int]:
        return asdict(self)


@dataclass(frozen=True)
class CoachAssessment:
    scores: CoachScores
    confidence: float
    top_gaps: List[str]
    reasons: List[str]
    ml_quality_prob: Optional[float] = None

    def to_dict(self) -> Dict:
        return {
            "scores": self.scores.to_dict(),
            "confidence": self.confidence,
            "top_gaps": self.top_gaps,
            "reasons": self.reasons,
            "ml_quality_prob": self.ml_quality_prob,
        }


class ScoringEngine:
    """
    Hybrid scoring engine:
      - Rule-based sub-scores (transparent + explainable)
      - Optional ML probability for overall call quality (real ML, trained offline)
    """

    def __init__(self, use_ml: bool = True) -> None:
        self._ml_model: Optional[CoachQualityModel] = None
        if use_ml:
            try:
                self._ml_model = CoachQualityModel()
            except Exception:
                self._ml_model = None

    def score(self, signals: CoachSignals) -> CoachAssessment:
        reasons: List[str] = []

        empathy = self._score_empathy(signals, reasons)
        pacing = self._score_pacing(signals, reasons)
        objection_handling = self._score_objection_handling(signals, reasons)
        closing = self._score_closing(signals, reasons)

        scores = CoachScores(
            empathy=empathy,
            pacing=pacing,
            objection_handling=objection_handling,
            closing=closing,
        )

        confidence = self._score_confidence(signals, reasons)
        top_gaps = self._pick_top_gaps(scores)

        ml_quality_prob: Optional[float] = None
        if self._ml_model:
            feats = {
                "empathy_hits": signals.empathy_hits,
                "objection_count": len(signals.objections),
                "closing_attempted": signals.closing_attempted,
                "long_monologue_lines": signals.long_monologue_lines,
                "total_lines": signals.total_lines,
            }
            try:
                ml_quality_prob = self._ml_model.predict_good_call_prob(feats)
                reasons.append(f"ML quality probability: {ml_quality_prob:.2f}")
            except Exception:
                ml_quality_prob = None

        return CoachAssessment(
            scores=scores,
            confidence=confidence,
            top_gaps=top_gaps,
            reasons=reasons[:6],
            ml_quality_prob=ml_quality_prob,
        )

    def _score_empathy(self, signals: CoachSignals, reasons: List[str]) -> int:
        score = min(100, signals.empathy_hits * 30)
        if signals.empathy_hits == 0:
            reasons.append("No empathy/acknowledgement phrases detected.")
        elif signals.empathy_hits >= 3:
            reasons.append("Multiple empathy/acknowledgement phrases detected.")
        return self._clamp(score)

    def _score_pacing(self, signals: CoachSignals, reasons: List[str]) -> int:
        score = 90 - (signals.long_monologue_lines * 20)
        if signals.long_monologue_lines >= 2:
            reasons.append("Several long monologue segments detected (pacing risk).")
        elif signals.long_monologue_lines == 0:
            reasons.append("No long monologue segments detected (healthy pacing).")
        return self._clamp(score)

    def _score_objection_handling(self, signals: CoachSignals, reasons: List[str]) -> int:
        if not signals.objections:
            reasons.append("No strong objections detected (limited objection-handling evidence).")
            return 75
        base = 70
        if signals.empathy_hits >= 2:
            base += 10
            reasons.append("Objections detected and empathy signals present (better handling likelihood).")
        else:
            base -= 15
            reasons.append("Objections detected but low empathy signals (handling may be weak).")

        base -= max(0, (len(signals.objections) - 1)) * 5
        return self._clamp(base)

    def _score_closing(self, signals: CoachSignals, reasons: List[str]) -> int:
        if signals.closing_attempted:
            reasons.append("Closing attempt detected (next step / demo / proposal).")
            return 85
        reasons.append("No closing attempt detected (missing clear next step).")
        return 45


    def _score_confidence(self, signals: CoachSignals, reasons: List[str]) -> float:
        lines_factor = min(1.0, signals.total_lines / 25.0)

        signal_factor = 0.0
        signal_factor += 0.25 if signals.empathy_hits > 0 else 0.0
        signal_factor += 0.25 if len(signals.objections) > 0 else 0.0
        signal_factor += 0.25 if signals.closing_attempted else 0.0
        signal_factor += 0.25 if signals.total_lines >= 10 else 0.0

        conf = 0.30 + (0.40 * lines_factor) + (0.30 * signal_factor)
        conf = max(0.0, min(1.0, conf))

        if conf < 0.55:
            reasons.append("Low confidence due to limited transcript evidence.")
        return conf

    def _pick_top_gaps(self, scores: CoachScores) -> List[str]:
        items: List[Tuple[str, int]] = [
            ("empathy", scores.empathy),
            ("pacing", scores.pacing),
            ("objection_handling", scores.objection_handling),
            ("closing", scores.closing),
        ]
        items_sorted = sorted(items, key=lambda x: x[1])
        return [items_sorted[0][0], items_sorted[1][0]]

    def _clamp(self, n: int) -> int:
        return max(0, min(100, int(n)))
