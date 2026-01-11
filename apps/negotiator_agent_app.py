# apps/negotiator_agent_app.py
from __future__ import annotations

import re
import time
from dataclasses import dataclass
from pathlib import Path
import traceback
import uuid
from typing import Any, Dict, List, Optional, Tuple
import textwrap



# --- Repo import path bootstrap ---

import os
import sys
import streamlit as st
st.set_page_config(page_title="Negotiator — Whisper Coach", layout="wide")
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

DOTENV_PATH = REPO_ROOT / ".env"
load_dotenv(dotenv_path=DOTENV_PATH, override=False)

# quick sanity check
# st.caption(f"dotenv_path={DOTENV_PATH} exists={DOTENV_PATH.exists()}")
# st.caption(f"GOOGLE_API_KEY present={bool(os.getenv('GOOGLE_API_KEY'))}")





from src.shared.kill_switch import KillSwitch

AGENT_NAME = "negotiator_agent"


# =============================================================================
# Styling (matches your screenshot vibe: clean cards, pills, coach panel)
# =============================================================================
def inject_css() -> None:
    st.markdown(
        """
        <style>
          .block-container { padding-top: 0.7rem; padding-bottom: 2rem; max-width: 1300px; }
          header[data-testid="stHeader"] { background: rgba(0,0,0,0); }
          [data-testid="stToolbar"] { visibility: hidden; height: 0; }

          /* Top bar */
          .topbar {
            display:flex; align-items:center; justify-content:space-between;
            padding: 10px 18px;
            border: 1px solid rgba(49,51,63,0.10);
            border-radius: 16px;
            background: rgba(255,255,255,0.02);
            margin-bottom: 14px;
          }
          .brand { display:flex; gap:10px; align-items:center; }
          .logo {
            width:34px; height:34px; border-radius:10px;
            display:flex; align-items:center; justify-content:center;
            background: rgba(79,70,229,0.12);
            border: 1px solid rgba(79,70,229,0.22);
            font-weight: 900;
          }
          .brand-title { font-size: 1.15rem; font-weight: 900; }
          .brand-sub { opacity: 0.7; font-size: 0.9rem; margin-top: -2px; }

          .pill {
            display:inline-flex; align-items:center; gap:8px;
            padding: 7px 12px; border-radius: 999px;
            border: 1px solid rgba(49,51,63,0.12);
            background: rgba(255,255,255,0.02);
            font-size: 0.88rem; font-weight: 800;
          }
          .dot { width:10px; height:10px; border-radius:50%; background: #22c55e; box-shadow: 0 0 0 4px rgba(34,197,94,0.18); }
          .dot-red { background: #ef4444; box-shadow: 0 0 0 4px rgba(239,68,68,0.18); }

          /* Cards */
          .card {
            border: 1px solid rgba(49,51,63,0.10);
            border-radius: 18px;
            background: rgba(255,255,255,0.02);
            padding: 18px;
          }
          .card-title { font-size: 1.05rem; font-weight: 900; margin-bottom: 6px; }
          .muted { opacity: 0.72; font-size: 0.92rem; }

          /* Live stream area */
          .stream-wrap {
            border: 1px solid rgba(49,51,63,0.10);
            border-radius: 18px;
            background: rgba(255,255,255,0.02);
            overflow: hidden;
          }
          .stream-head {
            display:flex; align-items:center; justify-content:space-between;
            padding: 14px 16px;
            border-bottom: 1px solid rgba(49,51,63,0.08);
          }
          .stream-title {
            display:flex; align-items:center; gap:10px;
            font-weight: 900;
          }
          .live-dot {
            width:10px; height:10px; border-radius: 50%;
            background: #ef4444;
            box-shadow: 0 0 0 4px rgba(239,68,68,0.16);
          }
          .monitor-pill {
            padding: 6px 12px; border-radius: 999px;
            font-weight: 800; font-size: 0.85rem;
            background: rgba(148,163,184,0.20);
            border: 1px solid rgba(148,163,184,0.25);
            color: rgba(255,255,255,0.85);
          }

          .stream-body {
            height: 540px;
            overflow-y: auto;
            padding: 16px;
          }

          /* Chat bubbles */
          .bubble-row { display:flex; margin: 10px 0; }
          .bubble {
            max-width: 78%;
            border-radius: 16px;
            padding: 12px 14px;
            border: 1px solid rgba(49,51,63,0.10);
            line-height: 1.35;
            font-weight: 650;
          }
          .cust { justify-content:flex-start; }
          .cust .bubble { background: rgba(148,163,184,0.14); }
          .rep { justify-content:flex-end; }
          .rep .bubble {
            background: rgba(79,70,229,0.92);
            color: white;
            border: 1px solid rgba(79,70,229,0.35);
          }
          .label {
            font-size: 0.72rem;
            font-weight: 900;
            letter-spacing: 0.04em;
            opacity: 0.70;
            margin-bottom: 6px;
          }

          /* Whisper coach */
          .coach-head {
            display:flex; align-items:center; justify-content:space-between;
            margin-bottom: 12px;
          }
          .coach-title {
            display:flex; gap:10px; align-items:center;
            font-weight: 950;
            font-size: 1.05rem;
          }
          .badge {
            padding: 5px 10px;
            border-radius: 999px;
            border: 1px solid rgba(49,51,63,0.12);
            background: rgba(255,255,255,0.02);
            font-weight: 900;
            font-size: 0.78rem;
            opacity: 0.85;
          }

          .whisper-card {
            border-radius: 18px;
            border: 1px solid rgba(49,51,63,0.10);
            background: rgba(255,255,255,0.02);
            padding: 14px 14px 12px 14px;
            margin-bottom: 14px;
            box-shadow: 0 12px 30px rgba(0,0,0,0.03);
          }

          .tone-pill {
            display:inline-flex; align-items:center; gap:8px;
            padding: 6px 10px;
            border-radius: 999px;
            font-weight: 900;
            font-size: 0.75rem;
            border: 1px solid rgba(49,51,63,0.10);
          }

          .tone-reassuring { background: rgba(34,197,94,0.10); }
          .tone-curious { background: rgba(245,158,11,0.12); }
          .tone-direct { background: rgba(59,130,246,0.12); }
          .tone-neutral { background: rgba(148,163,184,0.18); }

          .whisper-top {
            display:flex; align-items:center; justify-content:space-between;
            margin-bottom: 10px;
          }
          .conf {
            font-weight: 900;
            opacity: 0.7;
            font-size: 0.80rem;
          }

          .quote-box {
            border-radius: 14px;
            border: 1px solid rgba(49,51,63,0.10);
            background: rgba(255,255,255,0.02);
            padding: 12px 12px;
            font-style: italic;
            font-weight: 700;
          }

          .whisper-reason {
            margin-top: 10px;
            opacity: 0.70;
            font-size: 0.86rem;
            font-weight: 650;
          }

          /* Buttons */
          div.stButton > button {
            border-radius: 14px !important;
            padding: 0.7rem 0.9rem !important;
            font-weight: 900 !important;
          }
          textarea { border-radius: 14px !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )


# =============================================================================
# Real agent wiring (preferred) + safe fallback
# =============================================================================
REAL_AGENT_AVAILABLE = False
_real: Dict[str, Any] = {}

try:
    # Your real negotiator agent modules (already present in repo structure)
    from src.agents.negotiator_agent.decision_engine import DecisionEngine
    from src.agents.negotiator_agent.sentiment_engine import SentimentEngine
    from src.agents.negotiator_agent.objection_detector import ObjectionDetector
    from src.agents.negotiator_agent.llm_whisper_generator import LLMWhisperGenerator
    from src.agents.negotiator_agent.fallback_templates import FallbackTemplateGenerator
    from src.agents.negotiator_agent.feedback_logger import FeedbackLogger, FeedbackEvent

    _real["sentiment"] = SentimentEngine()
    _real["objection"] = ObjectionDetector()
    _real["llm"] = LLMWhisperGenerator()  # uses shared LLM client config if set
    _real["fallback"] = FallbackTemplateGenerator()
    _real["engine"] = DecisionEngine(
    llm_generator=_real["llm"],
    fallback_generator=_real["fallback"],
    # keep defaults, or tune these later
    min_soft_confidence=0.60,
    min_strong_confidence=0.80,
    context_window_n=4,
    negative_sentiment_trigger=0.70,
    )

    _real["fb_logger_cls"] = FeedbackLogger
    _real["fb_event_cls"] = FeedbackEvent
    REAL_AGENT_AVAILABLE = True
except Exception as e:
    REAL_AGENT_AVAILABLE = False
    st.error("Negotiator real-agent init failed (fallback mode).")
    st.code(str(e))
    st.code(traceback.format_exc())


# ---- Fallback (super-safe, regex only) ----
OBJECTION_PATTERNS = {
    "price": [r"\btoo expensive\b", r"\bexpensive\b", r"\bprice\b", r"\bcost\b", r"\bbudget\b"],
    "timing": [r"\bnot now\b", r"\blater\b", r"\bnext (week|month|quarter)\b", r"\bno time\b"],
    "competitor": [r"\bcompetitor\b", r"\busing (.+)\b", r"\balready have\b", r"\bwe use\b"],
    "trust": [r"\bnot sure\b", r"\bprove\b", r"\bhow do i know\b", r"\bguarantee\b"],
}
NEGATIVE = [r"\bfrustrated\b", r"\bannoyed\b", r"\bupset\b", r"\bdisappointed\b", r"\bissue\b", r"\bproblem\b"]
POSITIVE = [r"\bgreat\b", r"\bgood\b", r"\blove\b", r"\bamazing\b", r"\bperfect\b"]


def _detect_objection_fallback(text: str) -> Optional[str]:
    t = text.lower()
    for k, pats in OBJECTION_PATTERNS.items():
        for p in pats:
            if re.search(p, t):
                return k
    return None


def _sentiment_fallback(text: str) -> str:
    t = text.lower()
    if any(re.search(p, t) for p in NEGATIVE):
        return "negative"
    if any(re.search(p, t) for p in POSITIVE):
        return "positive"
    return "neutral"


def _suggest_fallback(objection: Optional[str], sentiment: str) -> Tuple[str, float, List[str]]:
    reasons = []
    if objection:
        reasons.append(f"Objection detected: {objection}")
    reasons.append(f"Sentiment: {sentiment}")

    if objection == "price":
        msg = (
            "I completely understand. To make this easier, would a phased rollout help reduce the initial cost "
            "while still solving your core need?"
        )
        conf = 0.82
        tone = "reassuring"
    elif objection == "timing":
        msg = "That makes sense. Is timing the main blocker, or just bandwidth? We can pick a small next step that fits."
        conf = 0.78
        tone = "curious"
    elif objection == "competitor":
        msg = "Got it. What do you like about your current tool, and what’s missing? If we solve the gap, would you compare?"
        conf = 0.76
        tone = "curious"
    elif objection == "trust":
        msg = "Fair question. What proof would you need—case study, a trial, or a quick demo tailored to your use case?"
        conf = 0.74
        tone = "direct"
    else:
        msg = "Thanks—tell me a bit more about what you’re trying to achieve and what matters most right now."
        conf = 0.62
        tone = "neutral"

    if sentiment == "negative":
        msg = "I hear you. " + msg
        conf = min(0.90, conf + 0.05)

    return msg, conf, [*reasons, f"Tone: {tone}"]


# =============================================================================
# UI helpers
# =============================================================================
@dataclass
class ChatLine:
    speaker: str  # "customer" | "rep"
    text: str


@dataclass
class WhisperSuggestion:
    sid: str
    tone: str
    call_id: str
    chunk_id: int
    generation_path: str

    # ✅ add these
    objection: str
    sentiment_label: str
    sentiment_confidence: float

    confidence: float
    text: str
    rationale: str
    chunk_idx: int


def _parse_transcript_lines(raw: str) -> List[ChatLine]:
    """
    Expects:
      Rep: ...
      Customer: ...
    One line per utterance is best.
    """
    out: List[ChatLine] = []
    for ln in [x.strip() for x in raw.splitlines() if x.strip()]:
        if ln.lower().startswith("rep:"):
            out.append(ChatLine("rep", ln.split(":", 1)[1].strip()))
        elif ln.lower().startswith("customer:"):
            out.append(ChatLine("customer", ln.split(":", 1)[1].strip()))
        else:
            # If no prefix, assume customer (safe)
            out.append(ChatLine("customer", ln))
    return out


def _chunk_lines(lines: List[ChatLine], chunk_size: int) -> List[List[ChatLine]]:
    chunks: List[List[ChatLine]] = []
    buf: List[ChatLine] = []
    for ln in lines:
        buf.append(ln)
        if len(buf) >= chunk_size:
            chunks.append(buf)
            buf = []
    if buf:
        chunks.append(buf)
    return chunks


def _tone_class(tone: str) -> str:
    t = (tone or "").lower()
    if "reass" in t:
        return "tone-reassuring"
    if "cur" in t:
        return "tone-curious"
    if "dir" in t:
        return "tone-direct"
    return "tone-neutral"


def _render_whisper_panel(
    suggestions: List[WhisperSuggestion],
    max_active: int,
    interactive: bool = True,
    panel_id: str = "main",
) -> None:


    active = suggestions[:max_active]
    st.markdown('<div class="card">', unsafe_allow_html=True)

    st.markdown(
        f"""
        <div class="coach-head">
          <div class="coach-title">⚡ Whisper Coach</div>
          <div class="badge">{len(active)} ACTIVE SUGGESTIONS</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not active:
        st.markdown(
            "<div class='muted'>No active whispers yet. Start streaming to generate live suggestions.</div>",
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)
        return

    for i, s in enumerate(active):
        kbase = f"{panel_id}_{s.sid}_{s.chunk_idx}_{i}"
        tone_cls = _tone_class(s.tone)
        conf_pct = int(round(float(s.confidence) * 100))

        st.markdown(
            f"""
            <div class="whisper-card">
              <div class="whisper-top">
                <div class="tone-pill {tone_cls}">TONE: {s.tone.upper() if s.tone else "NEUTRAL"}</div>
                <div class="conf">CONF: {conf_pct}%</div>
              </div>

              <div class="quote-box">
                “{s.text}”
              </div>

              <div class="whisper-reason">{s.rationale}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if interactive:
            b1, b2 = st.columns(2, gap="medium")
            with b1:
                if st.button("👍 ACCEPT", key=f"accept_{kbase}", use_container_width=True):
                    _log_feedback(s, action="accepted")
                    _remove_suggestion(s.sid)
                    st.rerun()
            with b2:
                if st.button("👎 IGNORE", key=f"ignore_{kbase}", use_container_width=True):
                    _log_feedback(s, action="ignored")
                    _remove_suggestion(s.sid)
                    st.rerun()
        else:
            st.caption("⏳ Streaming… Accept/Ignore will appear after streaming finishes.")

    if len(suggestions) > max_active:
        with st.expander(f"Show all suggestions ({len(suggestions)})"):
            for extra in suggestions[max_active:]:
                st.write(f"- {extra.text}")

    if s.generation_path == "fallback":
        st.caption("⚠️ Generated via fallback (LLM unavailable)")


    st.markdown("</div>", unsafe_allow_html=True)


def _ensure_state() -> None:
    st.session_state.setdefault("neg_is_running", False)
    st.session_state.setdefault("neg_chat_history", [])  # List[ChatLine as dict]
    st.session_state.setdefault("neg_suggestions", [])  # List[WhisperSuggestion as dict]
    st.session_state.setdefault("neg_last_run_id", 0)


def _push_chat(line: ChatLine) -> None:
    st.session_state["neg_chat_history"].append({"speaker": line.speaker, "text": line.text})


def _push_suggestion(s: WhisperSuggestion, max_keep: int = 20) -> None:
    # Keep newest at top
    existing = st.session_state["neg_suggestions"]
    existing.insert(0, s.__dict__)
    st.session_state["neg_suggestions"] = existing[:max_keep]


def _remove_suggestion(sid: str) -> None:
    st.session_state["neg_suggestions"] = [x for x in st.session_state["neg_suggestions"] if x.get("sid") != sid]


def _log_feedback(s: WhisperSuggestion, action: str) -> None:
    if not REAL_AGENT_AVAILABLE:
        return

    try:
        fb_logger = _real["fb_logger_cls"]()
        fb_logger.log(
            call_id=s.call_id,
            chunk_id=s.chunk_id,
            rep_action=action,
            objection=s.objection,
            sentiment_label=s.sentiment_label,
            confidence=float(s.confidence),
            strength="strong" if s.confidence >= 0.8 else "soft",
            generation_path=s.generation_path,
            edited_text=None,
        )

    except Exception as e:
        st.error("Feedback logging failed")
        st.code(str(e))

def _format_context_window(history: List[Dict[str, str]], window: int = 6) -> str:
    """
    Builds a compact multi-line context with speaker labels.
    """
    recent = history[-window:] if window > 0 else history
    lines = []
    for h in recent:
        sp = "Rep" if h["speaker"] == "rep" else "Customer"
        lines.append(f"{sp}: {h['text']}")
    return "\n".join(lines).strip()


def _decide_whisper_for_chunk(chunk_text: str, chunk_id: int) -> Optional[WhisperSuggestion]:
    """
    Returns WhisperSuggestion or None.
    Uses real Negotiator Agent pipeline if available; otherwise fallback.
    """
    # --- REAL PATH ---
    if REAL_AGENT_AVAILABLE:
        try:
            # Maintain a rolling context (like run_stream.py)
            st.session_state.setdefault("neg_context_window", [])
            ctx = st.session_state["neg_context_window"]
            ctx.append(chunk_text)
            ctx = ctx[-4:]  # keep last 4 chunks
            st.session_state["neg_context_window"] = ctx
            # Clean speaker labels for signal detection
            chunk_text_clean = (
                chunk_text
                .replace("Rep:", "")
                .replace("Customer:", "")
                .strip()
            )

            # Compute signals
            sentiment = _real["sentiment"].analyze(chunk_text_clean, context=ctx)
            objections = _real["objection"].detect(chunk_text_clean)


            # Call DecisionEngine with correct signature
            call_id = f"ui_call_{st.session_state.get('neg_last_run_id', 0)}"
            # chunk_id = len(st.session_state.get("neg_chat_history", []))  # simple, stable-ish id

            d = _real["engine"].decide(
                call_id=call_id,
                chunk_id=chunk_id,
                chunk_text=chunk_text_clean,  # ✅
                context_window=ctx,
                sentiment=sentiment,
                objections=objections,
            )

            if not (d.suggested_reply or "").strip():
                return None


            run_uuid = st.session_state.get("neg_run_uuid") or "no_run"
            sid = f"s_{run_uuid}_{uuid.uuid4().hex}"

            return WhisperSuggestion(
                sid=sid,
                call_id=d.call_id,
                chunk_id=d.chunk_id,
                generation_path=d.generation_path,
                tone=str(d.tone or "calm"),

                # ✅ add these 3
                objection=str(d.objection or "none"),
                sentiment_label=str(d.sentiment_label or "neutral"),
                sentiment_confidence=float(d.sentiment_confidence or 0.0),

                confidence=float(d.confidence or 0.0),
                text=str(d.suggested_reply).strip(),
                rationale=str(d.reason or "llm_generated").strip(),
                chunk_idx=0,
            )

        except Exception as e:
            st.error("Real engine decide() failed — falling back")
            st.code(str(e))
            st.code(traceback.format_exc())


    # --- FALLBACK PATH ---
    obj = _detect_objection_fallback(chunk_text)
    sent = _sentiment_fallback(chunk_text)
    msg, conf, reasons = _suggest_fallback(obj, sent)

    tone = "reassuring"
    for r in reasons:
        if r.lower().startswith("tone:"):
            tone = r.split(":", 1)[1].strip()

    run_uuid = st.session_state.get("neg_run_uuid") or "no_run"
    sid = f"s_{run_uuid}_{uuid.uuid4().hex}"

    return WhisperSuggestion(
        sid=sid,
        tone=tone,
        call_id="fallback_ui",
        chunk_id=0,
        generation_path="fallback",

        # ✅ add these 3
        objection=str(obj or "none"),
        sentiment_label=str(sent or "neutral"),
        sentiment_confidence=0.50,  # fallback doesn't compute confidence; pick a safe constant

        confidence=float(conf),
        text=str(msg).strip(),
        rationale="; ".join([x for x in reasons if not x.lower().startswith("tone:")]),
        chunk_idx=0,
    )



def _render_stream(chat_history: List[ChatLine], is_running: bool) -> None:
    monitor = "Monitoring..." if is_running else "Idle"
    MAX_RENDER_LINES = 80
    chat_history = chat_history[-MAX_RENDER_LINES:]


    bubbles_html: List[str] = []
    for line in chat_history:
        if line.speaker == "rep":
            bubbles_html.append(
                f"""
<div class="bubble-row rep">
  <div class="bubble">
    <div class="label">REP</div>
    {line.text}
  </div>
</div>
""".strip()
            )
        else:
            bubbles_html.append(
                f"""
<div class="bubble-row cust">
  <div class="bubble">
    <div class="label">CUSTOMER</div>
    {line.text}
  </div>
</div>
""".strip()
            )

    html = f"""
<div class="stream-wrap">
  <div class="stream-head">
    <div class="stream-title">
      <span class="live-dot"></span>
      <span>Live Transcription Stream</span>
    </div>
    <div class="monitor-pill">{monitor}</div>
  </div>

  <div class="stream-body">
    {''.join(bubbles_html)}
  </div>
</div>
"""

    st.markdown(html, unsafe_allow_html=True)




# =============================================================================
# Main render
# =============================================================================
def render_negotiator_app() -> None:
    inject_css()
    _ensure_state()

    ks = KillSwitch()
    global_disabled = bool(ks.get_state().global_disabled)
    agent_disabled = ks.is_disabled(AGENT_NAME)

    # Top bar
    if global_disabled or agent_disabled:
        status_label = "SYSTEM STATUS: DISABLED"
        dot_class = "dot dot-red"
    else:
        status_label = "LEVEL 1 — SHADOW MODE"
        dot_class = "dot"
    
    st.caption(f"REAL_AGENT_AVAILABLE={REAL_AGENT_AVAILABLE}")

    st.markdown(
        f"""
        <div class="topbar">
          <div class="brand">
            <div class="logo">▦</div>
            <div>
              <div class="brand-title">Negotiator</div>
              <div class="brand-sub">Real-time whisper coaching (rep stays in control)</div>
            </div>
          </div>
          <div class="pill">
            <span class="{dot_class}"></span>
            <span>{status_label}</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if global_disabled:
        st.error("Global Kill Switch is ON. Negotiator is suspended.")
        st.stop()

    if agent_disabled:
        st.error("Negotiator Agent is disabled by kill switch.")
        st.stop()

    # -----------------------------------------------------------------------------
    # Live Call Simulator (your second screenshot)
    # -----------------------------------------------------------------------------
    with st.container(border=True):
        st.markdown("## Live Call Simulator")
        st.markdown(
            "<div class='muted'>Paste a transcript, stream it in chunks, and show whisper suggestions.</div>",
            unsafe_allow_html=True,
        )

        c1, c2 = st.columns(2, gap="large")
        with c1:
            chunk_size = st.slider("Lines per chunk", min_value=1, max_value=6, value=2)
        with c2:
            delay = st.slider("Delay per chunk (sec)", min_value=0.0, max_value=2.0, value=0.4, step=0.1)

        demo = (
            "Rep: Hi Sam. This is Alex from ClearFollow. I’ll be brief. How much time do you have?\n"
            "Customer: About 10 minutes.\n"
            "Rep: Great. What made you look at our product?\n"
            "Customer: We’re missing follow-ups.\n"
            "Rep: Where specifically?\n"
            "Customer: After demos and trials.\n"
            "Rep: How are you handling that now?\n"
            "Customer: Spreadsheets and reminders.\n"
            "Customer: Honestly, I’m not sure we have the budget for this right now.\n"
            "Rep: That makes sense. Budget is always a concern.\n"
            "Customer: We’re also using SalesSync and they’re much cheaper.\n"
            "Rep: Got it — helpful context.\n"
            "Customer: What are the next steps if we wanted to explore this?\n"
        )
        transcript = st.text_area(
            "Transcript (one line per utterance works best)",
            height=240,
            value=st.session_state.get("neg_transcript_input", demo),
        )
        st.session_state["neg_transcript_input"] = transcript

        a1, a2, a3 = st.columns([0.22, 0.26, 0.52], gap="medium")
        with a1:
            if st.button("Reset session", use_container_width=True):
                st.session_state["neg_chat_history"] = []
                st.session_state["neg_suggestions"] = []
                st.session_state["neg_is_running"] = False
                st.rerun()
        with a2:
            start = st.button("Start whisper coaching ▶", type="primary", use_container_width=True)

        if not start:
            # Still show the “like screenshot” layout (empty state)
            left, right = st.columns([0.64, 0.36], gap="large")
            with left:
                # _render_stream_header(is_running=False)
                # _render_stream_body(chat_history=[ChatLine(**x) for x in st.session_state["neg_chat_history"]])
                _render_stream(
                    chat_history=[ChatLine(**x) for x in st.session_state["neg_chat_history"]],
                    is_running=False,
                )

            with right:
                _render_whisper_panel(
                    suggestions=[WhisperSuggestion(**x) for x in st.session_state["neg_suggestions"]],
                    max_active=3,
                    interactive=True,
                    panel_id="idle",
                )

            return

    # -----------------------------------------------------------------------------
    # Streaming run (shows your first screenshot layout)
    # -----------------------------------------------------------------------------
    if not transcript.strip():
        st.error("Transcript is empty.")
        return

    lines = _parse_transcript_lines(transcript)
    chunks = _chunk_lines(lines, chunk_size=chunk_size)

    # We will render “live” by iterating chunks; update chat history + suggestion queue.
    st.session_state["neg_is_running"] = True

    left, right = st.columns([0.64, 0.36], gap="large")

    # placeholders for live updates
    stream_ph = left.empty()
    coach_ph = right.empty()
    st.session_state["neg_last_run_id"] += 1

    # ✅ add here
    st.session_state["neg_run_uuid"] = uuid.uuid4().hex


    for idx, chunk in enumerate(chunks, start=1):
        # Append chunk lines to chat
        for ln in chunk:
            _push_chat(ln)

        # Decide whisper from the last customer-ish text or combined chunk text
        # Build full rolling context from chat history
        # Dynamic context window (stable across chunk sizes)
        window_n = max(8, chunk_size * 2)

        context_text = _format_context_window(
            st.session_state["neg_chat_history"],
            window=window_n,
        )


        # Only trigger whisper when the latest line in this chunk is from customer
        if any(ln.speaker == "customer" for ln in chunk):
            whisper = _decide_whisper_for_chunk(context_text, chunk_id=idx)
            if whisper:
                whisper.chunk_idx = idx
                _push_suggestion(whisper)



        # Render live layout
        with stream_ph.container():
            _render_stream(
                chat_history=[ChatLine(**x) for x in st.session_state["neg_chat_history"]],
                is_running=True,
            )

        with coach_ph.container():
            _render_whisper_panel(
                suggestions=[WhisperSuggestion(**x) for x in st.session_state["neg_suggestions"]],
                max_active=3,
                interactive=False,
                panel_id=f"stream_{idx}",
            )


        if delay and delay > 0:
            time.sleep(float(delay))

    st.session_state["neg_is_running"] = False
    st.success("Streaming finished. You can Accept/Ignore suggestions or Reset session.")
    with coach_ph.container():
        _render_whisper_panel(
            suggestions=[WhisperSuggestion(**x) for x in st.session_state["neg_suggestions"]],
            max_active=3,
            interactive=True,
            panel_id="final",
        )


if __name__ == "__main__":
    render_negotiator_app()
