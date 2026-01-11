from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
import textwrap
import streamlit.components.v1 as components
from dataclasses import is_dataclass, fields
from typing import Set
from dataclasses import MISSING
from datetime import datetime, timezone

import pandas as pd
import streamlit as st

# --- Repo import path bootstrap ---
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.shared.kill_switch import KillSwitch
from src.agents.retention_agent.feedback_logger import FeedbackLogger, FeedbackEvent

AGENT_NAME = "retention_agent"
OUTPUT_PATH = REPO_ROOT / "mock-data" / "outputs" / AGENT_NAME / "daily_output.json"
FEEDBACK_PATH = REPO_ROOT / "mock-data" / "feedback" / f"{AGENT_NAME}_feedback.jsonl"

DEBUG_MODE = False   # set True only for dev / evaluator

# ---------------------------
# Helpers
# ---------------------------
def _safe_list(x: Any) -> List[Any]:
    return x if isinstance(x, list) else []


def normalize_cards(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Accept both legacy and current retention batch schemas.
    """
    if isinstance(data.get("cards"), list):
        return data["cards"]

    if isinstance(data.get("customers"), list):
        cards = []
        for c in data["customers"]:
            cards.append(
                {
                    "customer_id": c.get("customer_id"),
                    "risk_band": c.get("risk_band"),
                    "churn_score": c.get("churn_score"),
                    "confidence": c.get("confidence"),
                    "top_reasons": c.get("reasons"),
                    "recommended_action": c.get("recommended_action"),
                    "next_step_guidance": c.get("next_step_hint"),
                    "debug": c.get("debug"),
                }
            )
        return cards

    return []


def _feedbackevent_fieldnames() -> Set[str]:
    """
    Supports dataclass + pydantic v1/v2 style models.
    """
    # dataclass
    if is_dataclass(FeedbackEvent):
        return {f.name for f in fields(FeedbackEvent)}

    # pydantic v2
    if hasattr(FeedbackEvent, "model_fields"):
        return set(getattr(FeedbackEvent, "model_fields").keys())

    # pydantic v1
    if hasattr(FeedbackEvent, "__fields__"):
        return set(getattr(FeedbackEvent, "__fields__").keys())

    # fallback
    return set(dir(FeedbackEvent))

def _make_feedback_event(
    customer_id: str,
    churn_score: float,
    recommended_action: str,
    notes: str,
    decision: str = "accepted",
) -> Any:
    """
    Build FeedbackEvent using only fields that actually exist.
    Also auto-fills required fields like timestamp_utc/action_taken if present.
    """
    fn = _feedbackevent_fieldnames()
    payload: Dict[str, Any] = {}

    def put_any(value: Any, candidates: List[str]) -> None:
        for k in candidates:
            if k in fn and k not in payload:
                payload[k] = value
                return

    # ---- Canonical values we can always provide ----
    now_utc = datetime.now(timezone.utc).isoformat()
    action_taken_value = decision  # "accepted" / "rejected" / "ignored" etc.

    # ---- Map UI concepts to schema ----
    put_any(customer_id, ["customer_id", "customer", "account_id", "id"])
    put_any(churn_score, ["churn_score", "score", "risk_score"])
    put_any(recommended_action, ["recommended_action", "recommendation", "recommended", "action_recommended"])
    put_any(notes, ["notes", "note", "comment", "feedback", "message"])

    # These two are required in YOUR schema:
    put_any(now_utc, ["timestamp_utc", "timestamp", "ts_utc", "created_at_utc", "created_at"])
    put_any(action_taken_value, ["action_taken", "decision", "outcome", "status", "user_action", "human_action", "action"])

    # ---- Ensure required dataclass fields are present (no more crashes) ----
    if is_dataclass(FeedbackEvent):
        for f in fields(FeedbackEvent):
            is_required = (f.default is MISSING) and (f.default_factory is MISSING)  # type: ignore
            if is_required and f.name in fn and f.name not in payload:
                # minimal safe defaults
                if f.name == "timestamp_utc":
                    payload[f.name] = now_utc
                elif f.name == "action_taken":
                    payload[f.name] = action_taken_value
                else:
                    payload[f.name] = None

    return FeedbackEvent(**payload)


@st.cache_data(show_spinner=False)
def load_daily_output() -> Dict[str, Any]:
    if not OUTPUT_PATH.exists():
        return {"cards": [], "_missing": True}
    try:
        data = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            data["_missing"] = False
            return data
        return {"cards": [], "_missing": False}
    except Exception:
        return {"cards": [], "_missing": False, "_parse_error": True}


def _risk_meta(risk_band: str) -> Dict[str, str]:
    r = (risk_band or "unknown").lower().strip()
    if r == "high":
        return {
            "label": "HIGH RISK",
            "pill_bg": "rgba(239, 68, 68, 0.14)",
            "pill_border": "rgba(239, 68, 68, 0.35)",
            "pill_text": "#ef4444",
            "card_tint": "rgba(239, 68, 68, 0.06)",
            "score_color": "#ef4444",
        }
    if r == "medium":
        return {
            "label": "MEDIUM RISK",
            "pill_bg": "rgba(245, 158, 11, 0.14)",
            "pill_border": "rgba(245, 158, 11, 0.35)",
            "pill_text": "#f59e0b",
            "card_tint": "rgba(245, 158, 11, 0.06)",
            "score_color": "#f59e0b",
        }
    if r == "low":
        return {
            "label": "LOW RISK",
            "pill_bg": "rgba(34, 197, 94, 0.14)",
            "pill_border": "rgba(34, 197, 94, 0.35)",
            "pill_text": "#16a34a",
            "card_tint": "rgba(34, 197, 94, 0.06)",
            "score_color": "#16a34a",
        }
    return {
        "label": "UNKNOWN",
        "pill_bg": "rgba(148, 163, 184, 0.16)",
        "pill_border": "rgba(148, 163, 184, 0.30)",
        "pill_text": "rgba(71, 85, 105, 0.95)",
        "card_tint": "rgba(148, 163, 184, 0.04)",
        "score_color": "rgba(71, 85, 105, 0.95)",
    }


def _pct(score01: Any) -> int:
    try:
        v = float(score01)
        if v > 1.0:  # just in case someone stores 0-100
            v = v / 100.0
        v = max(0.0, min(1.0, v))
        return int(round(v * 100))
    except Exception:
        return 0


def _as_float(x: Any) -> Optional[float]:
    try:
        if x is None:
            return None
        v = float(x)
        if pd.isna(v):
            return None
        return v
    except Exception:
        return None


# ---------------------------
# UI / CSS
# ---------------------------
def inject_css() -> None:
    st.markdown(
        """
        <style>
          .block-container { padding-top: 0.7rem; padding-bottom: 2rem; max-width: 1300px; }
          header[data-testid="stHeader"] { background: rgba(0,0,0,0); }
          [data-testid="stToolbar"] { visibility: hidden; height: 0; }

          /* Top bar (like your screenshot) */
          .topbar {
            display:flex; align-items:center; justify-content:space-between;
            margin: 4px 0 14px 0;
          }
          .topbar-title {
            font-size: 1.15rem;
            font-weight: 900;
            letter-spacing: -0.02em;
          }
          .status-pill {
            display:inline-flex; align-items:center; gap:8px;
            padding: 7px 12px;
            border-radius: 999px;
            border: 1px solid rgba(34,197,94,0.25);
            background: rgba(34,197,94,0.10);
            color: rgba(22, 101, 52, 1);
            font-weight: 900;
            font-size: 0.82rem;
          }
          .status-dot {
            width:10px; height:10px; border-radius: 50%;
            background: #22c55e;
            box-shadow: 0 0 0 4px rgba(34,197,94,0.16);
          }
          .status-pill.red {
            border: 1px solid rgba(239,68,68,0.25);
            background: rgba(239,68,68,0.10);
            color: rgba(153,27,27,1);
          }
          .status-dot.red {
            background: #ef4444;
            box-shadow: 0 0 0 4px rgba(239,68,68,0.16);
          }

          /* Header card */
          .header-card {
            border-radius: 18px;
            border: 1px solid rgba(49,51,63,0.10);
            background: rgba(255,255,255,0.02);
            padding: 18px;
            margin-bottom: 18px;
          }
          .h-title {
            font-size: 1.45rem;
            font-weight: 950;
            letter-spacing: -0.02em;
            margin: 0;
          }
          .h-sub {
            opacity: 0.72;
            font-size: 0.92rem;
            margin-top: 6px;
            font-weight: 650;
          }

          /* Cards grid */
          .ret-card {
            border-radius: 18px;
            border: 1px solid rgba(49,51,63,0.10);
            background: rgba(255,255,255,0.02);
            overflow: hidden;
            box-shadow: 0 18px 50px rgba(0,0,0,0.04);
          }
          .ret-card-inner {
            padding: 16px 16px 14px 16px;
          }
          .ret-head {
            display:flex; align-items:center; justify-content:space-between;
            gap: 10px;
            margin-bottom: 14px;
          }
          .ret-name {
            font-weight: 950;
            font-size: 1.02rem;
          }
          .risk-pill {
            padding: 6px 10px;
            border-radius: 999px;
            font-weight: 950;
            font-size: 0.74rem;
            letter-spacing: 0.03em;
            border: 1px solid rgba(49,51,63,0.10);
            white-space: nowrap;
          }

          .label {
            font-size: 0.74rem;
            font-weight: 900;
            letter-spacing: 0.05em;
            opacity: 0.55;
          }
          .score {
            font-size: 2.0rem;
            font-weight: 950;
            margin-top: 4px;
          }

          .indicator-wrap {
            margin-top: 10px;
          }
          .indicator {
            background: rgba(148,163,184,0.14);
            border: 1px solid rgba(148,163,184,0.16);
            border-radius: 10px;
            padding: 9px 10px;
            margin-top: 8px;
            font-size: 0.82rem;
            font-weight: 700;
            opacity: 0.90;
          }

          .rec-box {
            margin-top: 14px;
            border-radius: 14px;
            padding: 12px;
            border: 1px solid rgba(99,102,241,0.16);
            background: rgba(99,102,241,0.06);
          }
          .rec-title {
            font-size: 0.74rem;
            font-weight: 950;
            letter-spacing: 0.05em;
            color: rgba(79,70,229,1);
            display:flex; gap:8px; align-items:center;
            margin-bottom: 8px;
          }
          .rec-action {
            font-weight: 900;
            font-size: 0.92rem;
            color: rgba(30,41,59,0.95);
            line-height: 1.25;
          }
          .rec-quote {
            margin-top: 10px;
            font-style: italic;
            font-weight: 650;
            font-size: 0.82rem;
            color: rgba(79,70,229,0.75);
            line-height: 1.35;
          }

          .card-footer {
            padding: 10px 14px 14px 14px;
            border-top: 1px solid rgba(49,51,63,0.08);
            background: rgba(255,255,255,0.015);
          }

          /* Buttons */
          div.stButton > button {
            border-radius: 14px !important;
            padding: 0.78rem 1rem !important;
            font-weight: 900 !important;
          }

          /* Make text input look like search pill */
          div[data-testid="stTextInput"] input {
            border-radius: 14px !important;
          }
        </style>
        """,
        unsafe_allow_html=True,
    )

CARD_IFRAME_CSS = """
<style>
  body { margin:0; font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Arial; }
  .ret-card {
    border-radius: 18px;
    border: 1px solid rgba(49,51,63,0.10);
    overflow: hidden;
    box-shadow: 0 18px 50px rgba(0,0,0,0.04);
  }
  .ret-card-inner { padding: 16px 16px 14px 16px; }

  .ret-head {
    display:flex; align-items:center; justify-content:space-between;
    gap: 10px; margin-bottom: 14px;
  }
  .ret-name { font-weight: 950; font-size: 1.02rem; color: rgba(30,41,59,0.95); }

  .risk-pill {
    padding: 6px 10px;
    border-radius: 999px;
    font-weight: 950;
    font-size: 0.74rem;
    letter-spacing: 0.03em;
    white-space: nowrap;
  }

  .label {
    font-size: 0.74rem;
    font-weight: 900;
    letter-spacing: 0.05em;
    opacity: 0.55;
    color: rgba(30,41,59,0.85);
  }
  .score {
    font-size: 2.0rem;
    font-weight: 950;
    margin-top: 4px;
  }

  .indicator {
    background: rgba(148,163,184,0.14);
    border: 1px solid rgba(148,163,184,0.16);
    border-radius: 10px;
    padding: 9px 10px;
    margin-top: 8px;
    font-size: 0.82rem;
    font-weight: 700;
    color: rgba(30,41,59,0.92);
  }

  .rec-box {
    margin-top: 14px;
    border-radius: 14px;
    padding: 12px;
    border: 1px solid rgba(99,102,241,0.16);
    background: rgba(99,102,241,0.06);
  }
  .rec-title {
    font-size: 0.74rem;
    font-weight: 950;
    letter-spacing: 0.05em;
    color: rgba(79,70,229,1);
    margin-bottom: 8px;
  }
  .rec-action {
    font-weight: 900;
    font-size: 0.92rem;
    color: rgba(30,41,59,0.95);
    line-height: 1.25;
    text-transform: none;
  }
  .rec-quote {
    margin-top: 10px;
    font-style: italic;
    font-weight: 650;
    font-size: 0.82rem;
    color: rgba(79,70,229,0.75);
    line-height: 1.35;
  }
  .ret-card-inner {
    padding: 16px 16px 14px 16px;
    height: 380px;          /* fixed */
    overflow-y: auto;       /* scroll inside */
    }

</style>
"""



def _render_topbar(global_disabled: bool, agent_disabled: bool) -> None:
    if global_disabled or agent_disabled:
        pill_cls = "status-pill red"
        dot_cls = "status-dot red"
        label = "SYSTEM DISABLED"
    else:
        pill_cls = "status-pill"
        dot_cls = "status-dot"
        label = "Level 1 - Shadow Mode"

    st.markdown(
        f"""
        <div class="topbar">
          <div class="topbar-title">Retention</div>
          <div class="{pill_cls}">
            <span class="{dot_cls}"></span>
            <span>{label}</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _run_daily_batch_safe() -> None:
    """
    UI convenience button.
    Runs the retention daily batch locally (mock data) and refreshes the UI.
    """
    try:
        from src.agents.retention_agent.run_daily import run_daily_batch  # type: ignore

        with st.spinner("Processing daily batch..."):
            run_daily_batch()
        load_daily_output.clear()
        st.success("Daily batch processed ✅")
        st.rerun()
    except Exception as e:
        st.error(f"Could not run daily batch from UI. Run CLI instead.\n\nError: {e}")


def _render_header_card() -> None:
    st.markdown(
        """
        <div class="header-card">
          <div style="display:flex; align-items:center; justify-content:space-between; gap:14px;">
            <div>
              <div class="h-title">Retention Dashboard</div>
              <div class="h-sub">Analyzing weekly telemetry for churn indicators.</div>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _card_guidance(card: Dict[str, Any]) -> str:
    # prefer real guidance if present; else create a safe short one
    g = (card.get("next_step_guidance") or "").strip()
    if g:
        return g
    risk = (card.get("risk_band") or "unknown").lower()
    if risk == "high":
        return "Focus the conversation on the sharp usage drop and offer a guided health-check to restore adoption fast."
    if risk == "medium":
        return "Confirm obstacles, then propose a small adoption win (1 feature) and schedule a follow-up to measure progress."
    if risk == "low":
        return "Light-touch check-in: highlight wins and share one new feature tip to keep momentum."
    return "Review usage context and confirm whether an outreach is needed before taking action."


def _render_customer_card(card: Dict[str, Any]) -> None:
    cust = str(card.get("customer_id", "Unknown"))
    risk = (card.get("risk_band") or "unknown").lower()
    churn_pct = _pct(card.get("churn_score"))
    reasons = _safe_list(card.get("top_reasons") or card.get("reasons"))[:3]
    action = card.get("recommended_action", "—")
    guidance = card.get("next_step_guidance") or card.get("next_step_hint") or ""

    meta = _risk_meta(risk)
    btn_key = f"retain_{cust}_{risk}"

    indicators_html = (
        "".join([f"<div class='indicator'>{r}</div>" for r in reasons])
        if reasons
        else "<div class='indicator'>No strong churn signals detected.</div>"
    )

    card_html = f"""
    {CARD_IFRAME_CSS}
    <div class="ret-card" style="background:{meta['card_tint']};">
      <div class="ret-card-inner">

        <div class="ret-head">
          <div class="ret-name">{cust}</div>
          <div class="risk-pill" style="
            background:{meta['pill_bg']};
            border:1px solid {meta['pill_border']};
            color:{meta['pill_text']};
          ">
            {meta['label']}
          </div>
        </div>

        <div class="label">CHURN SCORE</div>
        <div class="score" style="color:{meta['score_color']};">{churn_pct}%</div>

        <div class="label" style="margin-top:12px;">PRIMARY INDICATORS</div>
        {indicators_html}

        <div class="rec-box">
          <div class="rec-title">🛡️ RECOMMENDED ACTION</div>
          <div class="rec-action">{action}</div>
          <div class="rec-quote">“{guidance}”</div>
        </div>

      </div>
    </div>
    """

    components.html(card_html, height=420, scrolling=False)

    if st.button("INITIATE RETENTION FLOW →", key=btn_key, use_container_width=True):
        fb = FeedbackLogger(FEEDBACK_PATH)  # Path, not str
        event = _make_feedback_event(
            customer_id=cust,
            churn_score=float(card.get("churn_score", 0.0)),
            recommended_action=action,
            notes="Initiated from dashboard (shadow mode)",
            decision="accepted",
        )

        fb.log(event)


        st.success("Retention flow logged (shadow mode) ✅")


# ---------------------------
# Main Render
# ---------------------------
def render_retention_app() -> None:
    st.set_page_config(page_title="Retention — Dashboard", layout="wide")
    inject_css()

    ks = KillSwitch()
    state = ks.get_state()
    global_disabled = bool(getattr(state, "global_disabled", False))
    agent_disabled = ks.is_disabled(AGENT_NAME)

    _render_topbar(global_disabled=global_disabled, agent_disabled=agent_disabled)

    if global_disabled:
        st.error("Global Kill Switch is ON. Retention is suspended.")
        st.stop()

    if agent_disabled:
        st.error("Retention Agent is disabled by kill switch.")
        st.stop()

    _render_header_card()

    # Search + Process button row (inside header area, like screenshot)
    left, mid, right = st.columns([0.58, 0.20, 0.22], gap="medium")
    with left:
        st.write("")  # spacing
    with mid:
        query = st.text_input(" ", placeholder="Filter customers...", label_visibility="collapsed")
    with right:
        if st.button("🔻  Process Daily Batch", type="primary", use_container_width=True):
            _run_daily_batch_safe()

    data = load_daily_output()
    if data.get("_missing"):
        st.info("No daily output found yet. Run: `python -m src.agents.retention_agent.run_daily`")
        return

    cards = normalize_cards(data)
    if query.strip():
        q = query.strip().lower()
        cards = [
            c for c in cards
            if q in str(c.get("customer_id") or "").lower()
            or q in str(c.get("account_id") or "").lower()
            or q in str(c.get("user_id") or "").lower()
        ]

    if not cards:
        st.warning("No customers match this filter.")
        return

    # 3-column grid like screenshot
    col1, col2, col3 = st.columns(3, gap="large")
    cols = [col1, col2, col3]

    for i, card in enumerate(cards):
        with cols[i % 3]:
            _render_customer_card(card)

    # Optional: tiny debug expander (kept but hidden)
    if DEBUG_MODE:
        with st.expander("Debug (raw daily_output.json)", expanded=False):
            st.json(data)

