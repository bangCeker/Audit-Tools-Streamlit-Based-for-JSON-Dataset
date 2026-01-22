# core/ui_helpers.py
from typing import Optional
import pandas as pd
import streamlit as st


def btn(
    label: str,
    *,
    stretch: bool = False,
    key: Optional[str] = None,
    on_click=None,
    args=None,
    disabled: bool = False,
    type: str = "secondary",
):
    try:
        return st.button(
            label,
            width=("stretch" if stretch else "content"),
            key=key,
            on_click=on_click,
            args=args,
            disabled=disabled,
            type=type,
        )
    except TypeError:
        return st.button(
            label,
            use_container_width=stretch,
            key=key,
            on_click=on_click,
            args=args,
            disabled=disabled,
        )


def submit(label: str, *, stretch: bool = True):
    try:
        return st.form_submit_button(label, width=("stretch" if stretch else "content"))
    except TypeError:
        return st.form_submit_button(label, use_container_width=stretch)


def data_editor(df: pd.DataFrame, *, key: str, disabled_cols=None, column_config=None):
    disabled_cols = disabled_cols or []
    column_config = column_config or {}
    try:
        return st.data_editor(
            df,
            key=key,
            width="stretch",
            hide_index=True,
            disabled=disabled_cols,
            column_config=column_config,
        )
    except TypeError:
        return st.data_editor(
            df,
            key=key,
            use_container_width=True,
            hide_index=True,
            disabled=disabled_cols,
            column_config=column_config,
        )
