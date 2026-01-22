# core/filters.py
import json
import streamlit as st
from core.config import AppConfig


def filters_dict():
    intent = None if st.session_state.f_intent == "(any)" else st.session_state.f_intent
    urg = None if st.session_state.f_urgency == "(any)" else st.session_state.f_urgency
    ev = None if st.session_state.f_event == "(any)" else st.session_state.f_event
    kw = (st.session_state.f_keyword or "").strip() or None
    return {"intent": intent, "urgency": urg, "event": ev, "keyword": kw}


def make_filter_sig() -> str:
    payload = {
        "table": st.session_state.get("table_name", ""),
        "filters": filters_dict(),
        "page_size": int(st.session_state.get("page_size", 50)),
    }
    return json.dumps(payload, sort_keys=True, ensure_ascii=False)


def ensure_page_reset_if_filters_changed(cfg: AppConfig) -> None:
    sig = make_filter_sig()
    if st.session_state.get("_filter_sig") != sig:
        st.session_state["_filter_sig"] = sig
        st.session_state.page = 0
