# apps/demo_app.py
from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

# --- Repo import path bootstrap ---
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.shared.kill_switch import KillSwitch

# Agent UIs
from apps.retention_agent_app import render_retention_app
from apps.negotiator_agent_app import render_negotiator_app
import apps.ai_sales_coach_app as ai_sales_coach_app


# ---------------------------
# CSS
# ---------------------------
def inject_css() -> None:
    st.markdown(
        """
        <style>
        .block-container { padding-top: 1.1rem; padding-bottom: 2rem; max-width: 1300px; }
        h1, h2, h3 { letter-spacing: -0.02em; }
        .react-caption { opacity: 0.8; font-size: 0.9rem; }

        section[data-testid="stSidebar"] {
            border-right: 1px solid rgba(49,51,63,0.15);
            background: #f6f7f9;
        }

        /* Sidebar navigation items */
        .nav-item {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 12px 14px;
            margin-bottom: 6px;
            border-radius: 12px;
            font-weight: 700;
            cursor: pointer;
            color: rgba(0,0,0,0.75);
            transition: background 0.15s ease;
        }

        .nav-item:hover {
            background: rgba(79,70,229,0.08);
        }

        .nav-item.active {
            background: rgba(79,70,229,0.14);
            color: #4f46e5;
        }

        .nav-icon {
            width: 22px;
            text-align: center;
            font-size: 1.05rem;
        }

        /* Make nav items clickable links (no ugly underline / spacing issues) */
        .nav-link {
            text-decoration: none !important;
            color: inherit !important;
            display: block;
        }

        .nav-link:visited, .nav-link:hover, .nav-link:active {
            text-decoration: none !important;
            color: inherit !important;
        }

        .nav-link { 
            -webkit-tap-highlight-color: transparent;
        }

        .nav-link * {
            pointer-events: none;   /* makes the whole row clickable (no weird partial click) */
        }


        </style>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------
# Main
# ---------------------------
def main() -> None:
    st.set_page_config(page_title="Agents Demo", layout="wide")
    inject_css()

    # ---------------------------
    # Session state init
    # ---------------------------
    if "active_agent" not in st.session_state:
        st.session_state["active_agent"] = "sales_coach"

    # Allow navigation via query param (HTML click)
    nav = st.query_params.get("nav")
    if isinstance(nav, list):
        nav = nav[0]
    if nav in {"sales_coach", "negotiator", "retention"}:
        st.session_state["active_agent"] = nav


    agent = st.session_state["active_agent"]

    # ---------------------------
    # Header
    # ---------------------------
    st.title("Sales Intelligence & Coaching Agents — Demo")
    st.caption(
        "One UI to demonstrate Negotiator, Retention, and AI Sales Coach "
        "(shadow-mode, human-in-control)."
    )

    ks = KillSwitch()

    # ---------------------------
    # Sidebar: Navigation
    # ---------------------------
    with st.sidebar:
        st.markdown("## SalesSphere")
        st.caption("Agent Navigation")

        def nav_item(label: str, key: str, icon: str):
            active = st.session_state["active_agent"] == key
            cls = "nav-item active" if active else "nav-item"

            st.markdown(
                f"""
                <a class="nav-link" href="?nav={key}" target="_self">
                    <div class="{cls}">
                        <div class="nav-icon">{icon}</div>
                        <div>{label}</div>
                    </div>
                </a>
                """,
                unsafe_allow_html=True,
            )


        nav_item("Sales Coach", "sales_coach", "🧠")
        nav_item("Negotiator", "negotiator", "🤝")
        nav_item("Retention", "retention", "📉")

    # ---------------------------
    # Sidebar: Kill Switch Controls
    # ---------------------------
    st.sidebar.markdown("---")
    st.sidebar.subheader("Kill Switch Controls")

    state = ks.get_state()
    global_disabled = bool(state.global_disabled)
    agents_state = dict(state.agents or {})

    with st.sidebar.form("kill_switch_form", clear_on_submit=False):
        g = st.toggle(
            "Global kill switch (disable ALL agents)",
            value=global_disabled,
        )

        st.caption("Per-agent toggles (only apply if global is OFF):")

        a1 = st.toggle(
            "ai_sales_coach enabled",
            value=not bool(agents_state.get("ai_sales_coach", False)),
            disabled=bool(g),
        )
        a2 = st.toggle(
            "retention_agent enabled",
            value=not bool(agents_state.get("retention_agent", False)),
            disabled=bool(g),
        )
        a3 = st.toggle(
            "negotiator_agent enabled",
            value=not bool(agents_state.get("negotiator_agent", False)),
            disabled=bool(g),
        )

        apply = st.form_submit_button("Apply changes")

    if apply:
        ks.set_global_disabled(bool(g))
        ks.set_agent_disabled("ai_sales_coach", not bool(a1))
        ks.set_agent_disabled("retention_agent", not bool(a2))
        ks.set_agent_disabled("negotiator_agent", not bool(a3))
        st.sidebar.success("Kill switch updated ✅")
        st.rerun()

    # ---------------------------
    # Sidebar: Status
    # ---------------------------
    st.sidebar.markdown("---")
    st.sidebar.caption("Kill Switch Status")

    def ks_badge(name: str):
        if ks.is_disabled(name):
            st.sidebar.error(f"{name}: DISABLED")
        else:
            st.sidebar.success(f"{name}: ENABLED")

    ks_badge("ai_sales_coach")
    ks_badge("retention_agent")
    ks_badge("negotiator_agent")

    # ---------------------------
    # Global kill switch UX
    # ---------------------------
    if ks.get_state().global_disabled:
        st.warning("🚨 Global kill switch is ON. All agents are paused.")
        if st.button("Turn OFF global kill switch"):
            ks.set_global_disabled(False)
            st.rerun()
        st.stop()

    # ---------------------------
    # Per-agent quick enable
    # ---------------------------
    agent_key_map = {
        "sales_coach": "ai_sales_coach",
        "retention": "retention_agent",
        "negotiator": "negotiator_agent",
    }

    current_agent_key = agent_key_map[agent]

    if ks.is_disabled(current_agent_key):
        st.info(f"⚠️ {agent.replace('_', ' ').title()} is disabled.")
        if st.button("Enable agent"):
            ks.set_agent_disabled(current_agent_key, False)
            st.rerun()

    # ---------------------------
    # Route
    # ---------------------------
    if agent == "sales_coach":
        ai_sales_coach_app.main()
    elif agent == "retention":
        render_retention_app()
    else:
        render_negotiator_app()


if __name__ == "__main__":
    main()
