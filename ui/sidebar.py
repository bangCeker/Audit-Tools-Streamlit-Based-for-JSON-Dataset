# ui/sidebar.py
import streamlit as st
from core.config import AppConfig

def render_sidebar(cfg: AppConfig) -> None:
    def _on_view_change():
        # kalau pindah ke single view via radio, paksa reload data dari DB
        if st.session_state.get("view_sel") == "Single Review":
            st.session_state["force_reload_single"] = True
            st.session_state["loaded_sig"] = None

    with st.sidebar:
        st.header("Dataset (DB)")
        st.selectbox("Table", ["dataset_train", "dataset_val", "dataset_test"], key="table_name")

        st.divider()
        st.radio("View", ["Table View", "Single Review"], key="view_sel", on_change=_on_view_change)

        st.divider()
        st.header("Filters")
        st.text_input("Keyword (text contains)", key="f_keyword")
        st.selectbox("Intent", ["(any)"] + cfg.INTENT, key="f_intent")
        st.selectbox("Urgency", ["(any)"] + cfg.URGENCY, key="f_urgency")
        st.selectbox("Event", ["(any)"] + cfg.EVENTS, key="f_event")

        st.divider()
        st.header("Pagination")
        st.selectbox("Page size", [25, 50, 100, 200], key="page_size")
