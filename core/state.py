# core/state.py
import streamlit as st
from core.config import AppConfig


def init_state(cfg: AppConfig) -> None:
    # data selection
    st.session_state.setdefault("table_name", "dataset_train")
    st.session_state.setdefault("page", 0)
    st.session_state.setdefault("page_size", 50)

    # selection + view
    st.session_state.setdefault("selected_id", None)
    st.session_state.setdefault("loaded_id", None)

    st.session_state.setdefault("loaded_sig", None)

    # NAV SAFE (jangan ubah key widget langsung)
    st.session_state.setdefault("view_sel", "Table View")   # widget key (radio)
    st.session_state.setdefault("nav_to_view", None)        # programmatic nav

    st.session_state.setdefault("force_reload_single", False)

    # edit state (single)
    st.session_state.setdefault("edit_text", "")
    st.session_state.setdefault("edit_intent", cfg.INTENT[0])
    st.session_state.setdefault("edit_urgency", cfg.URGENCY[1])
    st.session_state.setdefault("edit_events", [])
    st.session_state.setdefault("edit_note", "")

    # filters
    st.session_state.setdefault("f_keyword", "")
    st.session_state.setdefault("f_intent", "(any)")
    st.session_state.setdefault("f_urgency", "(any)")
    st.session_state.setdefault("f_event", "(any)")

    # auth state
    st.session_state.setdefault("auth_ok", False)
    st.session_state.setdefault("auth_user", None)

    # filter signature cache
    st.session_state.setdefault("_filter_sig", None)


def apply_nav_if_any() -> None:
    # apply programmatic nav BEFORE widgets instantiation
    nav = st.session_state.get("nav_to_view")
    if nav:
        st.session_state["view_sel"] = nav
        st.session_state["nav_to_view"] = None
