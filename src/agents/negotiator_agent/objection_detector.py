from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Tuple


@dataclass
class Objection:
    """
    Deterministic, auditable objection output.
    """
    label: str                  # price | timing | competitor | trust
    evidence: List[str]         # matched phrases/pattern names


class ObjectionDetector:
    """
    Rule-based objection detector (Phase 5.3 companion).
    Explainable by design: we store which patterns matched.
    """

    PATTERNS: Dict[str, List[Tuple[str, str]]] = {
        "price": [
            ("price_word", r"\bprice\b"),
            ("cost_word", r"\bcosts?\b"),
            ("reduce_costs_phrase", r"\breduce\s+costs?\b|\bcost\s+reduction\b"),
            ("budget_word", r"\bbudget\b"),
            ("expensive_word", r"\bexpensive\b"),
            ("too_expensive_phrase", r"\btoo expensive\b"),
            ("not_worth_phrase", r"\bnot worth\b"),
            ("afford_word", r"\bafford\b"),
            ("roi_phrase", r"\breturn on investment\b|\broi\b|\bjustif(?:y|ied|ication)\b"),
        ],

        "timing": [
            ("not_now_phrase", r"\bnot now\b"),
            ("later_word", r"\blater\b"),
            ("busy_phrase", r"\btoo busy\b|\bwe're busy\b|\bwe are busy\b"),
            ("this_quarter_phrase", r"\bthis quarter\b"),
            ("next_month_phrase", r"\bnext month\b"),
            ("timeline_word", r"\btimeline\b"),
            ("no_time_phrase", r"\bno time\b|\bdon't have time\b|\bdo not have time\b"),
            ("bandwidth_phrase", r"\bno bandwidth\b|\black bandwidth\b|\bbandwidth\b"),
            ("implementation_phrase", r"\bimplementation\b|\bimplement\b|\broll(?:out| out)\b"),
            ("resources_phrase", r"\bstretched thin\b|\boverloaded\b|\bresource constraints?\b|\bno resources\b"),
        ],

        "competitor": [
            ("competitor_word", r"\bcompetitor\b"),
            ("using_phrase", r"\bwe(?:'re|’re| are)?\s*(?:also\s*)?(?:use|using|are using|currently use|currently using)\b"),
            ("switch_word", r"\bswitch\b"),
            ("alternative_word", r"\balternative\b"),
            ("compare_word", r"\bcompare\b|\bcomparison\b|\bside-by-side\b"),
            ("versus_word", r"\bvs\b|\bversus\b"),
            ("already_have_phrase", r"\balready have\b|\balready using\b|\bwe have\b|\bwe've got\b|\bwe ve got\b"),
            ("current_tool_phrase", r"\bcurrent (?:tool|system|crm|platform)\b|\bexisting (?:tool|system|crm|platform)\b"),
        ],

        "trust": [
            ("skeptical_word", r"\bskeptical\b"),
            ("burned_phrase", r"\b(burned|burnt) (before|by)\b|\bbeen burned\b"),
            ("support_bad_phrase", r"\bterrible support\b|\bsupport was terrible\b"),
            ("dont_trust_phrase", r"\bdon't trust\b|\bdo not trust\b"),
            ("security_word", r"\bsecurity\b"),
            ("privacy_word", r"\bprivacy\b"),
            ("prove_it_phrase", r"\bprove it\b|\bproof\b|\bproof points\b"),
            ("worried_word", r"\bworr(y|ied)\b"),
        ],
    }

    # Priority order if multiple objections are present
    PRIORITY = ["trust", "price", "competitor", "timing"]

    def detect(self, chunk_text: str) -> List[Objection]:
        text = (chunk_text or "").lower()
        if not text.strip():
            return []

        found: Dict[str, List[str]] = {}

        for label, patterns in self.PATTERNS.items():
            hits: List[str] = []
            for name, pat in patterns:
                if re.search(pat, text, flags=re.IGNORECASE):
                    hits.append(name)
            if hits:
                found[label] = hits

        if not found:
            return []

        # Sort by priority order (trust first)
        objections: List[Objection] = []
        for label in self.PRIORITY:
            if label in found:
                objections.append(Objection(label=label, evidence=found[label]))

        # Include any other labels not in PRIORITY (future-proof)
        for label, hits in found.items():
            if label not in self.PRIORITY:
                objections.append(Objection(label=label, evidence=hits))

        return objections

    def primary_objection(self, objections: List[Objection]) -> str:
        """
        Returns the top objection label by priority. If none, returns "none".
        """
        if not objections:
            return "none"
        return objections[0].label
