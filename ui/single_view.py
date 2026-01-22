# ui/single_view.py
import json
import hashlib
import streamlit as st

from core.config import AppConfig
from core.ui_helpers import btn
from core.text_utils import normalize_text


def _load_into_edit_state(cfg: AppConfig, row: dict) -> None:
    st.session_state.edit_text = row.get("text") or ""
    st.session_state.edit_intent = row.get("intent") if row.get("intent") in cfg.INTENT else cfg.INTENT[0]
    st.session_state.edit_urgency = row.get("urgency") if row.get("urgency") in cfg.URGENCY else cfg.URGENCY[1]
    st.session_state.edit_events = [e for e in (row.get("events") or []) if e in cfg.EVENTS]
    st.session_state.edit_note = row.get("note", "") if isinstance(row.get("note", ""), str) else ""


def _row_content_sig(row: dict) -> str:
    payload = {
        "text": row.get("text") or "",
        "intent": row.get("intent") or "",
        "urgency": row.get("urgency") or "",
        "events": row.get("events") or [],
        "note": row.get("note") or "",
    }
    s = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.md5(s.encode("utf-8")).hexdigest()[:10]


def render_single_view(cfg: AppConfig, repo, f: dict) -> None:
    st.subheader("Single Review")
    table = st.session_state.get("table_name", "dataset_train")

    selected = st.session_state.get("selected_id")
    if not selected:
        st.info("Belum ada item dipilih. Buka dari Table View (centang open_single → Open in Single Review).")
        rid = st.number_input("Atau buka ID manual", min_value=1, value=1, step=1)
        if btn("Open ID", type="primary", key="btn_open_id"):
            st.session_state.selected_id = int(rid)
            st.session_state["loaded_sig"] = None
            st.rerun()

        st.divider()
        if btn("Back to Table View", stretch=True, key="btn_back_table_from_empty"):
            st.session_state.nav_to_view = "Table View"
            st.rerun()
        return

    rid = int(selected)
    row = repo.get_by_id(table, rid)
    if not row:
        st.error(f"ID {rid} tidak ditemukan di {table}.")
        if btn("Back to Table View", stretch=True, key="btn_back_table_notfound"):
            st.session_state.nav_to_view = "Table View"
            st.rerun()
        return

    # rec_sig berbasis konten -> kalau row berubah, auto reload state
    rec_sig = f"{table}:{rid}:{_row_content_sig(row)}"

    # reload jika:
    # - signature beda, atau
    # - edit_text kosong tapi row text tidak kosong (healing untuk bug blank)
    if (st.session_state.get("loaded_sig") != rec_sig) or (
        (st.session_state.get("edit_text") in [None, ""]) and (row.get("text") or "")
    ):
        st.session_state["loaded_sig"] = rec_sig
        _load_into_edit_state(cfg, row)

    def _save_current():
        it = st.session_state.edit_intent
        ur = st.session_state.edit_urgency
        ev = [e for e in (st.session_state.edit_events or []) if e in cfg.EVENTS]

        repo.update(
            table,
            rid,
            text=normalize_text(st.session_state.edit_text),
            intent=it,
            urgency=ur,
            events=ev,
            note=st.session_state.edit_note,
        )
        # setelah save, refresh signature biar sinkron
        st.session_state["loaded_sig"] = None

    def _cb_prev():
        pid = repo.adjacent_id(table, rid, "prev", **f)
        if pid is not None:
            st.session_state.selected_id = int(pid)
            st.session_state["loaded_sig"] = None
        else:
            st.toast("Tidak ada prev item (sudah pertama).", icon="ℹ️")

    def _cb_next():
        nid = repo.adjacent_id(table, rid, "next", **f)
        if nid is not None:
            st.session_state.selected_id = int(nid)
            st.session_state["loaded_sig"] = None
        else:
            st.toast("Tidak ada next item (sudah terakhir).", icon="ℹ️")

    def _cb_save_only():
        _save_current()
        st.toast("Saved ✓", icon="✅")

    def _cb_save_next():
        _save_current()
        _cb_next()

    left, right = st.columns([3, 2], gap="large")

    with left:
        st.markdown(f"**ID:** `{rid}`  |  **Table:** `{table}`")
        st.text_area("Text", key="edit_text", height=360)

    with right:
        st.selectbox("Intent", cfg.INTENT, key="edit_intent")
        st.selectbox("Urgency", cfg.URGENCY, key="edit_urgency")
        st.multiselect("Events", cfg.EVENTS, key="edit_events")
        st.text_input("Note (optional)", key="edit_note")

        st.divider()

        c1, c2 = st.columns(2)
        with c1:
            btn("⬅ Prev", stretch=True, on_click=_cb_prev, key="btn_prev_item")
        with c2:
            btn("Next ➡", stretch=True, on_click=_cb_next, key="btn_next_item")

        c3, c4 = st.columns(2)
        with c3:
            btn("💾 Save", stretch=True, type="primary", on_click=_cb_save_only, key="btn_save")
        with c4:
            btn("💾 Save + Next", stretch=True, on_click=_cb_save_next, key="btn_save_next")

        st.divider()
        if btn("Back to Table View", stretch=True, key="btn_back_table"):
            st.session_state.nav_to_view = "Table View"
            st.rerun()
