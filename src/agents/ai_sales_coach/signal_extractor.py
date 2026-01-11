#src/agents/ai_sales_coach/signal_extractor.py
from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from typing import Dict, List


@dataclass(frozen=True)
class CoachSignals:
    empathy_hits: int
    objections: List[str]       
    closing_attempted: bool
    long_monologue_lines: int
    total_lines: int

    def to_dict(self) -> Dict:
        return asdict(self)


class SignalExtractor:
    """
    Rule-based signal extractor for AI Sales Coach (v1).

    Input: full transcript text (string)
    Output: CoachSignals
    """
    EMPATHY_PATTERNS = [
        r"\bi understand\b",
        r"\bthat makes sense\b",
        r"\bi hear you\b",
        r"\bthanks for sharing\b",
        r"\bi appreciate\b",
        r"\bno worries\b",
        r"\btotally fair\b",
        r"\bthat's fair\b",
        r"\bfair point\b",
        r"\bunderstood\b",
        r"\bgot it\b",
        r"\bthat helps\b",
        r"\bhelpful context\b",
        r"\bgood question\b",
        r"\bthanks for (the )?context\b",
        r"\bthat’s common\b",
        r"\byou're not alone\b",
        r"\bi get why\b",
        r"\bi can see why\b",
    ]

    OBJECTION_PATTERNS = {
        "price": [
            r"\btoo expensive\b",
            r"\bexpensive\b",
            r"\bprice\b",
            r"\bcost\b",
            r"\bbudget\b",
            r"\bpricing\b",
            r"\bcan't afford\b",
            r"\btoo much\b",
            r"\bspend\b",

        ],
        "timing": [
            r"\bnot now\b",
            r"\blater\b",
            r"\bnext (month|quarter|week)\b",
            r"\bno time\b",
            r"\bmaybe (later|next)\b",
            r"\bnot a priority\b",
            r"\bafter (.*)quarter\b",
        ],
        "competitor": [
            r"\bcompetitor\b",
            r"\balready use\b",
            r"\busing (.*)\b", 
            r"\bother tool\b",
            r"\bwe're using\b",
            r"\busing (outreach|salesloft|hubspot|apollo|zoho|pipedrive)\b",
            r"\balternative\b",
        ],
        "trust": [
            r"\bnot sure\b",
            r"\bhow do i know\b",
            r"\bcan i trust\b",
            r"\bsecurity\b",
            r"\bprivacy\b",
            r"\bcompliance\b",
            r"\bsoc ?2\b",
            r"\bgdpr\b",
            r"\brisk\b",
        ],
    }

    CLOSING_PATTERNS = [
        r"\bnext step\b",
        r"\bschedule\b",
        r"\bbook\b",
        r"\bdemo\b",
        r"\btrial\b",
        r"\bproposal\b",
        r"\bcalendar invite\b",
        r"\bsend (you )?(a )?(quote|proposal|invite)\b",
        r"\bcan we move forward\b",
        r"\bwhat (does|would) (the )?timeline look like\b",
        r"\bdoes (next|tuesday|wednesday|thursday|friday)\b",
    ]

    def extract(self, transcript_text: str) -> CoachSignals:
        text = (transcript_text or "").strip()
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        lower_text = text.lower()

        empathy_hits = self._count_matches(lower_text, self.EMPATHY_PATTERNS)
        objections = self._detect_objections(lower_text)
        closing_attempted = self._has_any_match(lower_text, self.CLOSING_PATTERNS)

        long_monologue_lines = sum(1 for ln in lines if len(ln) >= 160)

        return CoachSignals(
            empathy_hits=empathy_hits,
            objections=objections,
            closing_attempted=closing_attempted,
            long_monologue_lines=long_monologue_lines,
            total_lines=len(lines),
        )

    def _count_matches(self, text: str, patterns: List[str]) -> int:
        hits = 0
        for pat in patterns:
            hits += len(re.findall(pat, text, flags=re.IGNORECASE))
        return hits

    def _has_any_match(self, text: str, patterns: List[str]) -> bool:
        for pat in patterns:
            if re.search(pat, text, flags=re.IGNORECASE):
                return True
        return False

    def _detect_objections(self, text: str) -> List[str]:
        found: List[str] = []
        for label, patterns in self.OBJECTION_PATTERNS.items():
            if self._has_any_match(text, patterns):
                found.append(label)
        return found
