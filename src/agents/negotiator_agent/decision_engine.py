from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from src.agents.negotiator_agent.sentiment_engine import SentimentResult
from src.agents.negotiator_agent.objection_detector import Objection
from src.agents.negotiator_agent.fallback_templates import FallbackTemplateGenerator, FallbackWhisper


@dataclass
class WhisperDecision:
    """
    Output contract from the Decision Engine.
    Used by OutputFormatter + Feedback Logger.
    """
    call_id: str
    chunk_id: int
    should_whisper: bool
    confidence: float  # 0..1
    strength: str      # "none" | "soft" | "strong"
    generation_path: str  # "llm" | "fallback" | "none"
    objection: str
    sentiment_label: str
    sentiment_confidence: float
    suggested_reply: Optional[str]
    tone: Optional[str]
    reason: str
    debug: Dict[str, Any]


class DecisionEngine:
    """
    Policy + routing engine for Negotiator Agent.

    - Uses objections + sentiment to decide whether to whisper.
    - Computes an auditable confidence score.
    - Uses LLM as PRIMARY generation path.
    - Falls back deterministically if LLM fails/invalid or confidence is not sufficient.
    """

    def __init__(
        self,
        *,
        llm_generator: Any,
        fallback_generator: FallbackTemplateGenerator,
        min_soft_confidence: float = 0.45,
        min_strong_confidence: float = 0.70,
        context_window_n: int = 4,
        negative_sentiment_trigger: float = 0.55,
    ) -> None:
        self.llm = llm_generator
        self.fallback = fallback_generator
        self.min_soft = float(min_soft_confidence)
        self.min_strong = float(min_strong_confidence)
        self.context_window_n = int(context_window_n)
        self.neg_trigger = float(negative_sentiment_trigger)

    def decide(
        self,
        *,
        call_id: str,
        chunk_id: int,
        chunk_text: str,
        context_window: List[str],
        sentiment: SentimentResult,
        objections: List[Objection],
    ) -> WhisperDecision:
        primary_obj = objections[0].label if objections else "none"

        # 1) Determine if we should consider whispering at all (trigger rules)
        triggered_by_objection = len(objections) > 0
        triggered_by_negative = (
            sentiment.label == "negative" and sentiment.confidence >= self.neg_trigger
        )

        should_consider = triggered_by_objection or triggered_by_negative

        if not should_consider:
            return WhisperDecision(
                call_id=call_id,
                chunk_id=chunk_id,
                should_whisper=False,
                confidence=0.0,
                strength="none",
                generation_path="none",
                objection=primary_obj,
                sentiment_label=sentiment.label,
                sentiment_confidence=sentiment.confidence,
                suggested_reply=None,
                tone=None,
                reason="no_trigger",
                debug={
                    "triggered_by_objection": triggered_by_objection,
                    "triggered_by_negative": triggered_by_negative,
                },
            )

        # 2) Compute whisper confidence (auditable, simple)
        confidence, conf_debug = self._compute_confidence(sentiment, objections)

        # 3) Gate by thresholds
        if confidence < self.min_soft:
            # Too uncertain: better to stay silent than distract rep
            return WhisperDecision(
                call_id=call_id,
                chunk_id=chunk_id,
                should_whisper=False,
                confidence=confidence,
                strength="none",
                generation_path="none",
                objection=primary_obj,
                sentiment_label=sentiment.label,
                sentiment_confidence=sentiment.confidence,
                suggested_reply=None,
                tone=None,
                reason="low_confidence_no_whisper",
                debug=conf_debug,
            )

        strength = "strong" if confidence >= self.min_strong else "soft"

        # 4) LLM-first generation (primary)
        llm_reason = "llm_primary"
        try:
            llm_out = self.llm.generate(
                chunk_text=chunk_text,
                context_window=context_window[-self.context_window_n :],
                sentiment_label=sentiment.label,
                objection=primary_obj,
                confidence=confidence,
            )
            # Expect dict with keys: suggested_reply, tone, objection, reason
            if self._valid_llm_output(llm_out):
                return WhisperDecision(
                    call_id=call_id,
                    chunk_id=chunk_id,
                    should_whisper=True,
                    confidence=confidence,
                    strength=strength,
                    generation_path="llm",
                    objection=str(llm_out.get("objection") or primary_obj),
                    sentiment_label=sentiment.label,
                    sentiment_confidence=sentiment.confidence,
                    suggested_reply=str(llm_out["suggested_reply"]).strip(),
                    tone=str(llm_out["tone"]).strip(),
                    reason="llm_generated",
                    debug=conf_debug | {"llm_used": True},
                )
            # Invalid output -> fallback
            fallback = self.fallback.generate(
                primary_obj,
                reason="llm_invalid_output",
                call_id=call_id,
                chunk_id=chunk_id,
                chunk_text=chunk_text,
                context_window=context_window[-self.context_window_n :],
            )

            return self._decision_from_fallback(
                call_id, chunk_id, sentiment, primary_obj, confidence, strength, fallback, conf_debug
            )

        except Exception:
            # Never leak raw LLM/provider errors to UI
            fallback = self.fallback.generate(
                primary_obj,
                reason="fallback_llm_unavailable",
                call_id=call_id,
                chunk_id=chunk_id,
                chunk_text=chunk_text,
                context_window=context_window[-self.context_window_n :],
            )

            return self._decision_from_fallback(
                call_id, chunk_id, sentiment, primary_obj, confidence, strength, fallback, conf_debug
            )


    def _decision_from_fallback(
        self,
        call_id: str,
        chunk_id: int,
        sentiment: SentimentResult,
        primary_obj: str,
        confidence: float,
        strength: str,
        fallback: FallbackWhisper,
        conf_debug: Dict[str, Any],
    ) -> WhisperDecision:
        return WhisperDecision(
            call_id=call_id,
            chunk_id=chunk_id,
            should_whisper=True,
            confidence=confidence,
            strength=strength,
            generation_path="fallback",
            objection=fallback.objection or primary_obj,
            sentiment_label=sentiment.label,
            sentiment_confidence=sentiment.confidence,
            suggested_reply=fallback.suggested_reply,
            tone=fallback.tone,
            reason=fallback.reason,
            debug=conf_debug | {"llm_used": False},
        )

    def _compute_confidence(
        self, sentiment: SentimentResult, objections: List[Objection]
    ) -> tuple[float, Dict[str, Any]]:
        """
        Confidence = base + objection evidence boost + negative sentiment boost (if applicable)
        Clamped to 0..1.
        """
        base = 0.50

        objection_boost = 0.0
        if objections:
            # Stronger if there is evidence and multiple hits
            top = objections[0]
            evidence_count = len(top.evidence)
            objection_boost += 0.20
            objection_boost += min(0.20, evidence_count * 0.05)  # up to +0.20

        sentiment_boost = 0.0
        if sentiment.label == "negative":
            # Use sentiment confidence directly but cap
            sentiment_boost += min(0.20, max(0.0, sentiment.confidence - 0.60))

        confidence = base + objection_boost + sentiment_boost
        confidence = max(0.0, min(1.0, confidence))

        debug = {
            "base": base,
            "objection_boost": objection_boost,
            "sentiment_boost": sentiment_boost,
            "computed_confidence": confidence,
            "top_objection": objections[0].label if objections else "none",
            "top_objection_evidence_count": len(objections[0].evidence) if objections else 0,
            "sentiment_label": sentiment.label,
            "sentiment_confidence": sentiment.confidence,
        }
        return confidence, debug

    def _valid_llm_output(self, llm_out: Any) -> bool:
        if not isinstance(llm_out, dict):
            return False

        required = ["suggested_reply", "tone", "objection"]
        for k in required:
            if k not in llm_out:
                return False

        reply = str(llm_out.get("suggested_reply") or "").strip()
        tone = str(llm_out.get("tone") or "").strip()
        objection = str(llm_out.get("objection") or "").strip()

        if not reply or not tone or not objection:
            return False

        # Keep it short: 1–2 lines max
        if reply.count("\n") > 1:
            return False
        if len(reply) > 280:
            return False

        # Basic safety: don't imply auto-actions
        banned = ["i will email", "i'll email", "sending you", "i will send you", "auto-send"]
        low = reply.lower()
        if any(b in low for b in banned):
            return False

        return True
