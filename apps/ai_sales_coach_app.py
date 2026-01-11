# apps/ai_sales_coach_app.py
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict

import streamlit as st

# --- Repo import path bootstrap ---
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.shared.kill_switch import KillSwitch
from src.agents.ai_sales_coach.signal_extractor import SignalExtractor
from src.agents.ai_sales_coach.scoring_engine import ScoringEngine
from src.agents.ai_sales_coach.tip_generator import generate_tips

AGENT_NAME = "ai_sales_coach"


# ---------------------------
# UI / CSS
# ---------------------------
def inject_css() -> None:
    st.markdown(
        """
        <style>
          .block-container { padding-top: 0.6rem; padding-bottom: 2rem; max-width: 1200px; }
          header[data-testid="stHeader"] { background: rgba(0,0,0,0); }

          /* Sidebar look */
          section[data-testid="stSidebar"] {
            border-right: 1px solid rgba(49,51,63,0.10);
            background: rgba(255,255,255,0.02);
          }

          /* Top bar */
          .topbar {
            display:flex; align-items:center; justify-content:space-between;
            padding: 10px 18px;
            border: 1px solid rgba(49,51,63,0.12);
            border-radius: 16px;
            background: rgba(255,255,255,0.03);
            margin-bottom: 18px;
          }
          .brand { display:flex; gap:10px; align-items:center; }
          .logo {
            width:34px; height:34px; border-radius:10px;
            display:flex; align-items:center; justify-content:center;
            background: rgba(80,120,255,0.14);
            border: 1px solid rgba(80,120,255,0.28);
            font-weight: 800;
          }
          .brand-title { font-size: 1.2rem; font-weight: 800; }
          .brand-sub { opacity: 0.7; font-size: 0.9rem; margin-top: -2px; }

          .pill {
            display:inline-flex; align-items:center; gap:8px;
            padding: 8px 12px; border-radius: 999px;
            border: 1px solid rgba(49,51,63,0.14);
            background: rgba(255,255,255,0.03);
            font-size: 0.88rem; font-weight: 700;
          }
          .dot { width:10px; height:10px; border-radius:50%; background: #2ecc71; box-shadow: 0 0 0 4px rgba(46,204,113,0.18); }
          .dot-red { background: #ff4d4d; box-shadow: 0 0 0 4px rgba(255,77,77,0.18); }

          /* Cards */
          .card {
            border: 1px solid rgba(49,51,63,0.12);
            border-radius: 18px;
            background: rgba(255,255,255,0.03);
            padding: 18px;
          }
          .card-title { font-size: 1.1rem; font-weight: 800; margin-bottom: 6px; }
          .muted { opacity: 0.75; font-size: 0.92rem; }

          /* Empty state */
          .bigpanel {
            border: 2px dashed rgba(120, 140, 170, 0.26);
            border-radius: 22px;
            min-height: 520px;
            background: rgba(255,255,255,0.02);
            padding: 28px;
            display:flex;
            align-items:center;
            justify-content:center;
            text-align:center;
          }
          .bigicon {
            width:64px; height:64px; border-radius: 999px;
            display:flex; align-items:center; justify-content:center;
            margin: 0 auto 14px auto;
            background: rgba(80,120,255,0.10);
            border: 1px solid rgba(80,120,255,0.22);
            font-weight: 900;
            font-size: 1.4rem;
          }
          .h1 { font-size: 1.8rem; font-weight: 900; margin: 0; }
          .spacer { height: 14px; }

          /* Buttons */
          div.stButton > button {
            border-radius: 14px !important;
            padding: 0.8rem 1rem !important;
            font-weight: 800 !important;
          }
          textarea { border-radius: 14px !important; }

          /* FULLSCREEN overlay modal (Global Kill Switch) */
          .ks-overlay {
            position: fixed;
            inset: 0;
            background: rgba(0,0,0,0.35);
            z-index: 99999;
            display:flex;
            align-items:center;
            justify-content:center;
            backdrop-filter: blur(6px);
          }
          .ks-modal {
            width: min(520px, 92vw);
            border-radius: 18px;
            border: 1px solid rgba(255, 100, 100, 0.35);
            background: rgba(255,255,255,0.92);
            padding: 22px 22px 18px 22px;
            box-shadow: 0 18px 60px rgba(0,0,0,0.25);
            text-align:center;
          }
          .ks-x {
            width: 56px; height: 56px; border-radius: 999px;
            display:flex; align-items:center; justify-content:center;
            margin: 0 auto 12px auto;
            border: 2px solid rgba(255, 80, 80, 0.55);
            color: rgba(255, 80, 80, 1);
            font-size: 26px;
            font-weight: 900;
          }
          .ks-title { font-size: 1.25rem; font-weight: 900; margin: 0; }
          .ks-desc { margin-top: 8px; color: rgba(40,40,40,0.75); font-weight: 600; font-size: 0.95rem; }
        
        /* ===== Score cards ===== */
            .score-card {
            border-radius: 18px;
            padding: 16px;
            border: 1px solid rgba(49,51,63,0.12);
            }

            .score-green {
            background: rgba(46, 204, 113, 0.10);
            }
            .score-amber {
            background: rgba(241, 196, 15, 0.12);
            }
            .score-red {
            background: rgba(231, 76, 60, 0.12);
            }

            .score-title {
            font-size: 0.85rem;
            font-weight: 800;
            letter-spacing: 0.04em;
            opacity: 0.85;
            }

            .score-value {
            font-size: 2rem;
            font-weight: 900;
            margin-top: 6px;
            }

            /* Progress bar */
            .progress-wrap {
            height: 8px;
            background: rgba(0,0,0,0.08);
            border-radius: 999px;
            overflow: hidden;
            margin: 10px 0;
            }
            .progress-bar {
            height: 100%;
            border-radius: 999px;
            }
            .pb-green { background: #2ecc71; }
            .pb-amber { background: #f1c40f; }
            .pb-red { background: #e74c3c; }

            /* ===== Coaching tips pills ===== */
            .tip-row {
            display: flex;
            gap: 12px;
            align-items: flex-start;
            margin-bottom: 14px;
            }
            .tip-pill {
            min-width: 34px;
            height: 34px;
            border-radius: 10px;
            background: #4f46e5;
            color: white;
            font-weight: 900;
            display: flex;
            align-items: center;
            justify-content: center;
            }
            .tip-text {
            font-size: 0.95rem;
            line-height: 1.4;
            }
        
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_system_suspended_overlay() -> None:
    st.markdown(
        """
        <div class="ks-overlay">
          <div class="ks-modal">
            <div class="ks-x">✕</div>
            <div class="ks-title">System Suspended</div>
            <div class="ks-desc">
              The Global Kill Switch is active. All AI agents have been disabled for safety and maintenance.
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _get_global_disabled_fast(ks: KillSwitch) -> bool:
    """
    Fast path:
    - keep global kill switch state in session_state
    - refresh from disk only once per session (or after toggle)
    """
    if "ks_global_disabled" not in st.session_state:
        st.session_state["ks_global_disabled"] = bool(ks.get_state().global_disabled)
    return bool(st.session_state["ks_global_disabled"])


def _set_global_disabled_fast(ks: KillSwitch, value: bool) -> None:
    st.session_state["ks_global_disabled"] = bool(value)
    ks.set_global_disabled(bool(value))


def demo_transcript() -> str:
    return (
        "Rep: Hey! Thanks for taking the time today. Before we jump in, what are you hoping to solve this quarter?\n"
        "Customer: We’re struggling to keep up with inbound leads and the team misses follow-ups.\n"
        "Rep: That makes sense — I hear you. When leads come in, where do they usually get stuck?\n"
        "Customer: Mostly assignment and reminders. We tried a competitor tool but it felt complex.\n"
        "Rep: Got it. If we could simplify routing and automate reminders, would that help reduce the drop-off?\n"
        "Customer: Possibly, but price is a concern.\n"
        "Rep: Totally fair. If we can show ROI by improving response time and conversion, would you be open to a quick demo?\n"
        "Customer: Maybe next week.\n"
        "Rep: Great — let’s book 20 minutes Tuesday. I’ll send a calendar invite and a short agenda.\n"
    )


def _render_scores(scores: Dict[str, Any]) -> None:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Empathy", scores.get("empathy", "—"))
    c2.metric("Pacing", scores.get("pacing", "—"))
    c3.metric("Objection", scores.get("objection_handling", "—"))
    c4.metric("Closing", scores.get("closing", "—"))

def render_post_call_header() -> None:
    st.markdown("### Post-Call Intelligence")
    st.caption("Submit your completed call transcripts for a deep-dive analysis.")



def render_score_cards_row(scores: Dict[str, Any]) -> None:
    def tone(v: int):
        if v >= 80:
            return "green"
        if v >= 60:
            return "amber"
        return "red"

    c1, c2, c3, c4 = st.columns(4, gap="medium")

    def card(col, title, value, subtitle):
        v = int(value) if isinstance(value, (int, float)) else 0
        t = tone(v)
        with col:
            st.markdown(
                f"""
                <div class="score-card score-{t}">
                  <div class="score-title">{title}</div>
                  <div class="score-value">{v}</div>
                  <div class="progress-wrap">
                    <div class="progress-bar pb-{t}" style="width:{v}%"></div>
                  </div>
                  <div class="muted">{subtitle}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    card(c1, "EMPATHY", scores.get("empathy", 0), "Empathy signals detected.")
    card(c2, "PACING", scores.get("pacing", 0), "Monologues / pacing signals.")
    card(c3, "OBJECTION HANDLING", scores.get("objection_handling", 0), "Adjusted using objections + empathy.")
    card(c4, "CLOSING", scores.get("closing", 0), "Closing signals present.")


def render_tips_and_reliability(tips: list[str], confidence: Any) -> None:
    """
    Two-column layout:
    Left: Coaching Tips (3)
    Right: Reliability (confidence)
    """
    left, right = st.columns([0.66, 0.34], gap="large")

    with left:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("### 💬 Coaching Tips")

        for i, t in enumerate((tips or [])[:3], start=1):
            st.markdown(
                f"""
                <div class="tip-row">
                <div class="tip-pill">{i}</div>
                <div class="tip-text">{t}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown("</div>", unsafe_allow_html=True)



    with right:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("### 📊 Reliability")
        if isinstance(confidence, (int, float)):
            st.markdown(f"<div style='font-size:52px; font-weight:900; text-align:center;'>{int(confidence*100)}%</div>", unsafe_allow_html=True)
            st.markdown("<div style='text-align:center; opacity:.7; font-weight:700;'>CONFIDENCE SCORE</div>", unsafe_allow_html=True)
        else:
            st.markdown("<div style='text-align:center; opacity:.8;'>—</div>", unsafe_allow_html=True)
        st.markdown("<hr style='opacity:.15;'>", unsafe_allow_html=True)
        st.caption("Scores are rule-based for auditability. Natural language generated by LLM (bounded).")
        st.markdown("</div>", unsafe_allow_html=True)





# ---------------------------
# Main
# ---------------------------
def main() -> None:
    st.set_page_config(page_title="AI Sales Coach Pro", layout="wide")
    inject_css()

    ks = KillSwitch()

    # --- GLOBAL kill switch (overrides agent) ---
    global_disabled = _get_global_disabled_fast(ks)
    agent_disabled = ks.is_disabled(AGENT_NAME)
    disabled = bool(global_disabled or agent_disabled)

    # ---------------------------
    # Sidebar: Security (Global Kill Switch)
    # ---------------------------
    with st.sidebar:
        st.markdown("## Security")
        new_global = st.toggle("Global Kill Switch", value=global_disabled, key="ui_global_kill")

        # Only write + rerun if changed (feels instant)
        if bool(new_global) != bool(global_disabled):
            _set_global_disabled_fast(ks, bool(new_global))
            st.rerun()

    # Top bar
    if global_disabled:
        status_label = "SYSTEM STATUS: SUSPENDED"
        dot_class = "dot dot-red"
    elif agent_disabled:
        status_label = "SYSTEM STATUS: DISABLED"
        dot_class = "dot dot-red"
    else:
        status_label = "LEVEL 1 — SHADOW MODE"
        dot_class = "dot"

    st.markdown(
        f"""
        <div class="topbar">
          <div class="brand">
            <div class="logo">▦</div>
            <div>
              <div class="brand-title">AI Sales Coach <span style="opacity:.75">Pro</span></div>
              <div class="brand-sub">Post-call coaching insights (no automation)</div>
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

    # If GLOBAL kill switch is ON, show modal and stop
    if global_disabled:
        render_system_suspended_overlay()
        st.stop()

    if agent_disabled:
        st.warning("AI Sales Coach is disabled by kill switch. Viewing is allowed, analysis is blocked.")


    # Keep results in session
    if "coach_result" not in st.session_state:
        st.session_state["coach_result"] = None

    # MAIN container card like screenshot
    st.markdown('<div class="card">', unsafe_allow_html=True)

    clicked_analyze = render_post_call_header()

        # User input transcript (paste call)
    transcript = st.text_area(
        "Call Transcript",
        value=st.session_state.get("transcript_input", ""),
        placeholder="Paste the completed call transcript here (2–3 mins).",
        height=160,
        disabled=disabled,
    )
    st.session_state["transcript_input"] = transcript

    # Small actions row like a real app
    a1, a2, _ = st.columns([0.18, 0.22, 0.60])
    with a1:
        if st.button("Insert Demo", disabled=disabled):
            st.session_state["transcript_input"] = demo_transcript()
            st.rerun()
    with a2:
        clicked_analyze_text = st.button("Analyze Transcript", type="primary", disabled=disabled)

    # Analyze trigger = either mock button OR transcript button
    run_analysis = bool(clicked_analyze or clicked_analyze_text)


    # If clicked analyze, run using transcript (or demo if empty)
    if run_analysis and not disabled:
        if not transcript.strip():
            transcript = demo_transcript()


        extractor = SignalExtractor()
        scorer = ScoringEngine(use_ml=True)

        signals = extractor.extract(transcript)
        assessment = scorer.score(signals)

        perf_summary = {
            "call_id": "mock_call",
            "rep_id": "rep_01",
            "signals": signals.to_dict(),
            "scores": assessment.scores.to_dict(),
            "top_gaps": assessment.top_gaps,
            "confidence": assessment.confidence,
            "ml_quality_prob": assessment.ml_quality_prob,
        }

        tips = generate_tips(performance_summary=perf_summary, top_gaps=assessment.top_gaps)

        st.session_state["coach_result"] = {
            "scores": assessment.scores.to_dict(),
            "top_gaps": assessment.top_gaps,
            "confidence": assessment.confidence,
            "ml_quality_prob": assessment.ml_quality_prob,
            "reasons": assessment.reasons,
            "tips": tips,
        }

    result = st.session_state.get("coach_result")

    if not result:
        # Empty state inside the card
        st.markdown(
            """
            <div class="bigpanel">
              <div>
                <div class="bigicon">📄</div>
                <div class="h1">Post-Call Intelligence</div>
                <div class="muted" style="margin-top:10px;">
                  No active analysis. Click “Analyze Mock Call” to process a sample call.
                </div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        render_score_cards_row(result["scores"])
        st.markdown("<div class='spacer'></div>", unsafe_allow_html=True)
        render_tips_and_reliability(
            tips=result.get("tips", []),
            confidence=result.get("confidence"),
        )
                # Reasons section
        st.markdown("<div class='spacer'></div>", unsafe_allow_html=True)
        with st.expander("Reasons (Why these scores?)", expanded=False):
            reasons = result.get("reasons", [])
            if not reasons:
                st.write("No reasons available.")
            else:
                for r in reasons:
                    st.write(f"- {r}")


    st.markdown("</div>", unsafe_allow_html=True)  # end MAIN card



if __name__ == "__main__":
    main()
