from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class SentimentResult:
    """
    Output contract for Phase 5.2:
    - label: positive | neutral | negative
    - confidence: 0..1 (how sure we are)
    - score: signed numeric score (debug)
    - reasons: short explainable reasons (auditable)
    """
    label: str
    confidence: float
    score: float
    reasons: List[str]


class SentimentEngine:
    """
    ML-lite sentiment for Negotiator Agent.

    We intentionally avoid heavy training/inference for this project.
    This uses a transparent lexicon + simple scoring to produce:
    - sentiment label
    - confidence estimate
    """

    # Minimal lexicons (safe + extendable)
    POSITIVE = {
        "great", "good", "awesome", "love", "like", "helpful", "perfect",
        "sounds good", "makes sense", "excited", "happy", "works"
    }
    NEGATIVE = {
        # general negatives
        "bad", "hate", "annoying", "frustrated", "frustrating", "confusing",
        "terrible", "waste", "disrupt", "risk",

        # objection-ish negatives (single words)
        "worried", "worry", "worries",
        "concerned", "concern", "concerns",
        "skeptical", "burned",
        "pressure", "bandwidth", "overloaded", "overwhelmed",

        # price/value negatives
        "expensive", "too expensive", "not worth",

        # reliability negatives
        "doesn't work", "does not work",

        # phrase-level negatives (your engine supports this already)
        "under pressure",
        "stretched thin",
        "no bandwidth",
        "lack bandwidth",
        "no time",
        "implementation worries",
    }


    INTENSIFIERS = {"very", "really", "super", "extremely", "totally"}
    NEGATORS = {"not", "no", "never", "can't", "cannot", "don't", "doesn't", "didn't"}

    def analyze(self, chunk_text: str, context: Optional[List[str]] = None) -> SentimentResult:
        """
        Analyze only the provided chunk. Context is optional and used
        only to slightly stabilize confidence (no deep memory).
        """
        text = (chunk_text or "").strip().lower()
        if not text:
            return SentimentResult(
                label="neutral",
                confidence=0.3,
                score=0.0,
                reasons=["empty_chunk"],
            )

        # Score the chunk with transparent rules
        pos_hits, neg_hits, reasons = self._score_lexicon(text)

        # Compute signed score
        score = float(pos_hits - neg_hits)

        label = self._label_from_score(score, pos_hits, neg_hits)

        # Confidence estimate: increases with more evidence and stronger imbalance
        confidence = self._confidence_from_hits(pos_hits, neg_hits)

        # Optional: if recent context strongly contradicts, soften confidence a bit
        if context:
            confidence = self._stabilize_with_context(confidence, label, context)

        return SentimentResult(
            label=label,
            confidence=confidence,
            score=score,
            reasons=reasons,
        )

    def _score_lexicon(self, text: str) -> tuple[int, int, List[str]]:
        """
        Counts lexicon hits. Also applies simple handling for negation and intensifiers.
        """
        reasons: List[str] = []

        # Token-ish list (simple and safe)
        tokens = [t.strip(".,!?;:()[]{}\"'") for t in text.split()]
        token_set = set(tokens)

        # Phrase hits
        pos_hits = 0
        neg_hits = 0

        # Phrase-level checks first
        for phrase in self.POSITIVE:
            if " " in phrase and phrase in text:
                pos_hits += 1
                reasons.append(f"pos_phrase:{phrase}")

        for phrase in self.NEGATIVE:
            if " " in phrase and phrase in text:
                neg_hits += 1
                reasons.append(f"neg_phrase:{phrase}")

        # Word-level checks
        for w in tokens:
            if w in self.POSITIVE:
                pos_hits += 1
                reasons.append(f"pos_word:{w}")
            if w in self.NEGATIVE:
                neg_hits += 1
                reasons.append(f"neg_word:{w}")

        # Negation handling (very lightweight):
        # if "not" appears immediately before a positive term, treat it as negative evidence.
        for i in range(len(tokens) - 1):
            if tokens[i] in self.NEGATORS and tokens[i + 1] in self.POSITIVE:
                # flip one hit from positive -> negative
                pos_hits = max(0, pos_hits - 1)
                neg_hits += 1
                reasons.append(f"negated_positive:{tokens[i]}_{tokens[i+1]}")

        # Intensifier handling:
        # if intensifier before negative word/phrase, slightly boost negativity
        for i in range(len(tokens) - 1):
            if tokens[i] in self.INTENSIFIERS and tokens[i + 1] in self.NEGATIVE:
                neg_hits += 1
                reasons.append(f"intensified_negative:{tokens[i]}_{tokens[i+1]}")

        # Keep reasons short if nothing matched
        if pos_hits == 0 and neg_hits == 0:
            reasons.append("no_lexicon_hits")

        return pos_hits, neg_hits, reasons

    def _label_from_score(self, score: float, pos_hits: int, neg_hits: int) -> str:
        # Neutral if no evidence
        if pos_hits == 0 and neg_hits == 0:
            return "neutral"

        # Small margins treated as neutral (avoid overreacting)
        if abs(score) < 1.0:
            return "neutral"

        return "positive" if score > 0 else "negative"

    def _confidence_from_hits(self, pos_hits: int, neg_hits: int) -> float:
        total = pos_hits + neg_hits
        if total == 0:
            return 0.35  # weak neutral

        imbalance = abs(pos_hits - neg_hits)

        # Base confidence grows with total evidence, then capped
        base = 0.45 + min(0.35, total * 0.10)  # up to +0.35
        # Imbalance boosts confidence (clearer sentiment)
        boost = min(0.20, imbalance * 0.10)

        conf = base + boost
        return max(0.0, min(1.0, conf))

    def _stabilize_with_context(self, confidence: float, label: str, context: List[str]) -> float:
        """
        If context indicates opposite sentiment frequently, reduce confidence slightly.
        This prevents "jitter" from single-word spikes.
        """
        ctx = " ".join(context[-3:]).lower()  # last few chunks only
        ctx_pos = any(p in ctx for p in self.POSITIVE if " " in p) or any(w in ctx.split() for w in self.POSITIVE)
        ctx_neg = any(n in ctx for n in self.NEGATIVE if " " in n) or any(w in ctx.split() for w in self.NEGATIVE)

        if label == "positive" and ctx_neg and not ctx_pos:
            return max(0.0, confidence - 0.10)
        if label == "negative" and ctx_pos and not ctx_neg:
            return max(0.0, confidence - 0.10)

        return confidence
