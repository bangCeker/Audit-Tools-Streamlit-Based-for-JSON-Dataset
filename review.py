# review_app.py
import streamlit as st

import db_helper as db

from core.config import load_config
from core.state import init_state, apply_nav_if_any
from core.auth import require_login
from core.filters import ensure_page_reset_if_filters_changed, filters_dict
from data.repo_db import DBRepo

from ui.sidebar import render_sidebar
from ui.table_view import render_table_view
from ui.single_view import render_single_view

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main():
    cfg = load_config()

    st.set_page_config(page_title=cfg.APP_TITLE, layout="wide")

    init_state(cfg)

    # auth gate (akan st.stop() kalau belum login)
    require_login(cfg)

    # NAV SAFE: apply perpindahan view sebelum widget sidebar dibuat
    apply_nav_if_any()

    # sidebar controls
    render_sidebar(cfg)

    # reset page kalau filter berubah
    ensure_page_reset_if_filters_changed(cfg)

    repo = DBRepo(db)

    f = filters_dict()

    if st.session_state.view_sel == "Table View":
        render_table_view(cfg, repo, f)
    else:
        render_single_view(cfg, repo, f)


if __name__ == "__main__":
    main()
