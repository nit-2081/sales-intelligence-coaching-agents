from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional
import hashlib


@dataclass
class FallbackWhisper:
    suggested_reply: str
    tone: str
    objection: str
    reason: str


class FallbackTemplateGenerator:
    """
    Deterministic but non-repetitive fallback for whisper suggestions.

    - Uses variant banks per objection (multiple replies).
    - Avoids repeating the same reply back-to-back per call_id + objection.
    - Can lightly personalize based on chunk/context keywords.
    """

    def __init__(self) -> None:
        # Each objection has multiple variants
        self.templates: Dict[str, Dict[str, List[str]]] = {
            "price": {
                "tone": ["curious", "curious", "reassuring"],
                "reply": [
                    "Totally fair. What budget range are you working with, and what outcome matters most so I can map value to that?",
                    "Makes sense. If we could tie this directly to a measurable result, what number would make it a ‘yes’?",
                    "I hear you. Would a smaller pilot or phased rollout help reduce the upfront cost while proving value?",
                    "Understood. Is the concern the total cost, or the timing of when that spend hits the budget?",
                ],
            },
            "timing": {
                "tone": ["curious", "calm", "curious"],
                "reply": [
                    "That makes sense. What would need to change for this to become a priority?",
                    "Got it — is it a ‘not now’ or a ‘not this quarter’ situation?",
                    "If we made this super lightweight, what timeline would feel realistic to explore?",
                    "What’s the key event or deadline that would drive action on this?",
                ],
            },
            "competitor": {
                "tone": ["curious", "curious", "reassuring"],
                "reply": [
                    "Got it — what do you like about your current tool, and what’s missing?",
                    "Makes sense. If you could improve one thing about your current setup, what would it be?",
                    "Totally fair. Which feature is the main reason you’re sticking with them right now?",
                    "If we were clearly better in one area, what would matter most: cost, workflow, or reporting?",
                ],
            },
            "trust": {
                "tone": ["reassuring", "curious", "calm"],
                "reply": [
                    "Fair question. What would give you confidence — proof points, security details, or a short pilot?",
                    "Totally valid. Would references from similar teams help, or a quick technical walkthrough?",
                    "Makes sense. What’s your biggest risk if this doesn’t work the way you expect?",
                    "If we can show results quickly, what’s the smallest safe step you’d be comfortable taking?",
                ],
            },
            "none": {
                "tone": ["calm", "curious", "curious"],
                "reply": [
                    "Got it. What’s the one thing you’re hoping to improve most right now?",
                    "Before we go deeper — what does success look like for you in the next 30–60 days?",
                    "Quick check: what’s driving you to explore options at the moment?",
                    "What’s currently taking the most time or causing the most friction for the team?",
                ],
            },
        }

        # Tracks last used variant per call+objection to prevent repetition
        self._last_variant_key: Dict[str, int] = {}

    def generate(
        self,
        objection: str,
        *,
        reason: str = "fallback_used",
        call_id: Optional[str] = None,
        chunk_id: Optional[int] = None,
        chunk_text: str = "",
        context_window: Optional[List[str]] = None,
    ) -> FallbackWhisper:
        key = (objection or "none").strip().lower()
        if key not in self.templates:
            key = "none"

        context_window = context_window or []
        full_ctx = " ".join([chunk_text] + context_window).lower()

        tpl = self.templates[key]
        replies = tpl["reply"]
        tones = tpl["tone"]

        # Deterministic seed (stable) so the UI is consistent for the same call/chunk
        seed_src = f"{call_id or ''}:{key}:{chunk_id if chunk_id is not None else ''}:{chunk_text[:40]}"
        seed = int(hashlib.md5(seed_src.encode("utf-8")).hexdigest(), 16)

        idx = seed % len(replies)

        # Anti-repeat: if same call+objection repeats, bump index
        if call_id:
            mem_key = f"{call_id}:{key}"
            last = self._last_variant_key.get(mem_key)
            if last is not None and last == idx:
                idx = (idx + 1) % len(replies)
            self._last_variant_key[mem_key] = idx

        reply = replies[idx]
        tone = tones[idx % len(tones)]

        # Light personalization (no ML): tweak line based on keywords
        if "crm" in full_ctx:
            reply = reply.replace("workflow", "CRM workflow")
        if "manual" in full_ctx or "follow-up" in full_ctx or "follow ups" in full_ctx:
            # add one small clause (still short)
            if reply.endswith("?"):
                reply = reply[:-1] + " — especially around manual follow-ups?"

        return FallbackWhisper(
            suggested_reply=reply,
            tone=tone,
            objection=key,
            reason=reason,
        )
