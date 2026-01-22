# ui/table_view.py
import math
import hashlib
from typing import Dict, Any, List

import pandas as pd
import streamlit as st

from core.config import AppConfig
from core.filters import make_filter_sig
from core.ui_helpers import btn, data_editor


def _inject_table_css():
    st.markdown(
        """
        <style>
          /* overall spacing */
          .block-container { padding-top: 1.2rem; }

          /* make fonts a bit smaller */
          html, body, [class*="css"] { font-size: 14px !important; }

          /* data editor look */
          [data-testid="stDataEditor"] {
            border: 1px solid rgba(255,255,255,0.10);
            border-radius: 14px;
            overflow: hidden;
          }

          /* inputs */
          [data-testid="stDataEditor"] input {
            border-radius: 10px !important;
            padding: 10px 10px !important;
          }

          /* nice section title */
          .mz-title {
            font-size: 18px;
            font-weight: 800;
            margin: 0;
          }
          .mz-muted { opacity: 0.75; font-size: 13px; }

          /* “card” container */
          .mz-card {
            border: 1px solid rgba(255,255,255,0.10);
            border-radius: 16px;
            padding: 14px 14px;
            background: rgba(255,255,255,0.02);
          }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _build_table_df(cfg: AppConfig, rows: List[Dict[str, Any]]) -> pd.DataFrame:
    data = []
    for r in rows:
        ev_set = set(r.get("events") or [])
        item = {
            "id": int(r["id"]),
            "text": (r.get("text") or ""),
            "intent": r.get("intent") or "",
            "urgency": r.get("urgency") or "",
            "open_single": False,
        }
        # events as checkbox columns
        for ev in cfg.EVENTS:
            item[f"EV_{ev}"] = (ev in ev_set)
        data.append(item)

    cols = ["id", "text", "intent", "urgency", "open_single"] + [f"EV_{e}" for e in cfg.EVENTS]
    return pd.DataFrame(data, columns=cols)


def _apply_table_edits(cfg: AppConfig, repo, table: str, df_before: pd.DataFrame, df_after: pd.DataFrame) -> int:
    """
    Update only changed rows to DB.
    Returns number of updated rows.
    """
    updated = 0

    # index by id for diff
    before_map = {int(r["id"]): r for r in df_before.to_dict(orient="records")}
    after_rows = df_after.to_dict(orient="records")

    for r in after_rows:
        rid = int(r["id"])
        b = before_map.get(rid)
        if not b:
            continue

        # reconstruct events
        new_events = [ev for ev in cfg.EVENTS if bool(r.get(f"EV_{ev}", False))]

        changed = False
        payload = {}

        # text
        new_text = (r.get("text") or "").strip()
        if new_text != (b.get("text") or "").strip():
            payload["text"] = new_text
            changed = True

        # intent / urgency
        new_intent = (r.get("intent") or "").strip()
        new_urg = (r.get("urgency") or "").strip()

        if new_intent != (b.get("intent") or ""):
            payload["intent"] = new_intent
            changed = True

        if new_urg != (b.get("urgency") or ""):
            payload["urgency"] = new_urg
            changed = True

        # events compare
        old_events = [ev for ev in cfg.EVENTS if bool(b.get(f"EV_{ev}", False))]
        if old_events != new_events:
            payload["events"] = new_events
            changed = True

        if not changed:
            continue

        # validate labels (biar ga nyimpen aneh)
        if payload.get("intent") and payload["intent"] not in cfg.INTENT:
            continue
        if payload.get("urgency") and payload["urgency"] not in cfg.URGENCY:
            continue

        repo.update(table, rid, **payload)
        updated += 1

    return updated


def render_table_view(cfg: AppConfig, repo, f: dict) -> None:
    _inject_table_css()

    table = st.session_state.table_name
    total = repo.count(table, **f)

    page_size = int(st.session_state.page_size)
    pages = max(1, math.ceil(total / page_size))
    st.session_state.page = max(0, min(int(st.session_state.page), pages - 1))
    offset = st.session_state.page * page_size

    rows = repo.query(table, limit=page_size, offset=offset, **f)

    st.markdown(
        f"""
        <div class="mz-card">
          <div class="mz-title">Table View</div>
          <div class="mz-muted">Table: <b>{table}</b> • Total: <b>{total}</b> • Page: <b>{st.session_state.page + 1}/{pages}</b></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.write("")

    # build df
    df_before = _build_table_df(cfg, rows)

    # editor key stable by filter signature + page
    sig_src = make_filter_sig()
    sig = hashlib.md5(sig_src.encode("utf-8")).hexdigest()[:10]
    editor_key = f"table_editor_{table}_{st.session_state.page}_{sig}"

    # column config
    col_cfg = {
        "id": st.column_config.NumberColumn("ID", disabled=True, width="small"),
        "text": st.column_config.TextColumn("Text", width="large"),
        "intent": st.column_config.SelectboxColumn("Intent", options=cfg.INTENT, required=False, width="small"),
        "urgency": st.column_config.SelectboxColumn("Urgency", options=cfg.URGENCY, required=False, width="small"),
        "open_single": st.column_config.CheckboxColumn("Open", width="small"),
    }
    for ev in cfg.EVENTS:
        col_cfg[f"EV_{ev}"] = st.column_config.CheckboxColumn(ev, width="small")

    topL, topR, topS = st.columns([4, 2, 2], vertical_alignment="center")
    with topL:
        st.caption("Edit langsung di tabel (Text/Intent/Urgency/Events). Lalu klik **Save changes**.")
    with topR:
        open_clicked = btn("Open Single Review", stretch=True, type="primary", key="btn_open_single")
    with topS:
        save_clicked = btn("💾 Save changes", stretch=True, key="btn_save_table")

    df_after = data_editor(
        df_before,
        key=editor_key,
        disabled_cols=["id"],  # yang lain boleh diedit
        column_config=col_cfg,
    )

    # actions
    if save_clicked:
        n = _apply_table_edits(cfg, repo, table, df_before, df_after)
        st.toast(f"Saved: {n} row(s)", icon="✅")
        st.rerun()

    if open_clicked:
        sel = df_after[df_after["open_single"] == True]
        if len(sel) == 0:
            st.warning("Centang kolom **Open** pada row yang mau dibuka.")
        else:
            rid = int(sel.iloc[0]["id"])
            st.session_state.selected_id = rid
            st.session_state.loaded_id = None
            st.session_state.loaded_sig = None   # penting: paksa reload di Single View biar nggak blank
            st.session_state.nav_to_view = "Single Review"
            st.rerun()

    st.divider()

    # pagination bottom (rapi)
    navL, navM, navR = st.columns([2, 3, 2], vertical_alignment="center")

    with navL:
        c1, c2 = st.columns(2)
        with c1:
            if btn("⬅ Prev", stretch=True, disabled=(st.session_state.page <= 0), key="btn_prev_page"):
                st.session_state.page -= 1
                st.rerun()
        with c2:
            if btn("Next ➡", stretch=True, disabled=(st.session_state.page >= pages - 1), key="btn_next_page"):
                st.session_state.page += 1
                st.rerun()

    with navM:
        st.markdown(f"**Page {st.session_state.page + 1} / {pages}**")
        st.caption(f"Showing {len(rows)} rows • page_size={page_size}")

    with navR:
        jump = st.number_input(
            "Jump page",
            label_visibility="collapsed",
            min_value=1,
            max_value=pages,
            value=st.session_state.page + 1,
            step=1,
        )
        if int(jump) != (st.session_state.page + 1):
            st.session_state.page = int(jump) - 1
            st.rerun()
