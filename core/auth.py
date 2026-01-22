# core/auth.py
import json
import os
import time
import hashlib
import hmac
import secrets as pysecrets
import streamlit as st

from core.config import AppConfig
from core.ui_helpers import btn
from ui.login_view import render_login_page


def _now_ts() -> int:
    return int(time.time())


def _sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _token_hash(cfg: AppConfig, tok: str) -> str:
    return hashlib.sha256((cfg.APP_SALT + "|" + (tok or "")).encode("utf-8")).hexdigest()


def _load_auth_store(cfg: AppConfig) -> dict:
    path = cfg.AUTH_STORE_PATH
    if not os.path.exists(path):
        return {"tokens": {}}
    try:
        with open(path, "r", encoding="utf-8") as f:
            obj = json.load(f)
        if not isinstance(obj, dict):
            return {"tokens": {}}
        if "tokens" not in obj or not isinstance(obj["tokens"], dict):
            obj["tokens"] = {}
        return obj
    except Exception:
        return {"tokens": {}}


def _save_auth_store(cfg: AppConfig, obj: dict) -> None:
    path = cfg.AUTH_STORE_PATH
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def _cleanup_expired_tokens(cfg: AppConfig, store: dict) -> dict:
    now = _now_ts()
    tokens = store.get("tokens", {})
    dead = []
    for th, meta in list(tokens.items()):
        exp = int(meta.get("exp", 0) or 0)
        if exp and exp < now:
            dead.append(th)
    for th in dead:
        tokens.pop(th, None)
    store["tokens"] = tokens
    if dead:
        _save_auth_store(cfg, store)
    return store


def _get_query_token(cfg: AppConfig) -> str:
    k = cfg.QP_TOKEN_KEY
    try:
        qp = st.query_params
        t = qp.get(k, "")
        if isinstance(t, list):
            t = t[0] if t else ""
        return str(t or "")
    except Exception:
        qp = st.experimental_get_query_params()
        t = qp.get(k, [""])
        return str(t[0] if t else "")


def _set_query_token(cfg: AppConfig, token: str | None):
    k = cfg.QP_TOKEN_KEY
    try:
        if token:
            st.experimental_set_query_params(**{k: token})
        else:
            st.experimental_set_query_params()
    except Exception:
        # ignore if not supported
        pass


def _invalidate_token(cfg: AppConfig, token: str):
    if not token:
        return
    th = _token_hash(cfg, token)
    store = _cleanup_expired_tokens(cfg, _load_auth_store(cfg))
    store["tokens"].pop(th, None)
    _save_auth_store(cfg, store)


def require_login(cfg: AppConfig) -> None:
    if os.getenv("DEV_NO_AUTH", "0") == "1":
        st.session_state["auth_ok"] = True
        st.session_state["auth_user"] = "DEV"
        return

    st.session_state.setdefault("auth_ok", False)
    st.session_state.setdefault("auth_user", None)

    if not cfg.APP_SALT or not cfg.APP_PASS_SHA256:
        st.error("Secrets belum diisi. Isi .streamlit/secrets.toml: APP_USER, APP_SALT, APP_PASS_SHA256")
        st.stop()

    # 1) auto-login from token
    if not st.session_state["auth_ok"]:
        tok = _get_query_token(cfg)
        if tok:
            store = _cleanup_expired_tokens(cfg, _load_auth_store(cfg))
            th = _token_hash(cfg, tok)
            meta = store.get("tokens", {}).get(th)
            if meta:
                exp = int(meta.get("exp", 0) or 0)
                if exp == 0 or exp >= _now_ts():
                    st.session_state["auth_ok"] = True
                    st.session_state["auth_user"] = str(meta.get("user", cfg.APP_USER))
                else:
                    _invalidate_token(cfg, tok)
                    _set_query_token(cfg, None)

    # 2) if logged in -> sidebar logout
    if st.session_state["auth_ok"]:
        with st.sidebar:
            st.success(f"Logged in as: {st.session_state.get('auth_user') or cfg.APP_USER}")
            if btn("Logout", stretch=True, key="logout_btn"):
                tok = _get_query_token(cfg)
                _invalidate_token(cfg, tok)
                _set_query_token(cfg, None)
                st.session_state["auth_ok"] = False
                st.session_state["auth_user"] = None
                st.rerun()
        return

    # 3) render login page
    u, p, remember, do_login = render_login_page(cfg.APP_BRAND, cfg.LOGIN_HERO_URL)

    if do_login:
        ok_user = (u.strip() == cfg.APP_USER)
        calc = _sha256_hex((cfg.APP_SALT + (p or "")).strip())
        ok_pass = hmac.compare_digest(calc, cfg.APP_PASS_SHA256)

        if ok_user and ok_pass:
            st.session_state["auth_ok"] = True
            st.session_state["auth_user"] = cfg.APP_USER

            if remember:
                tok = pysecrets.token_urlsafe(32)
                th = _token_hash(cfg, tok)
                store = _cleanup_expired_tokens(cfg, _load_auth_store(cfg))
                exp = _now_ts() + (cfg.AUTH_TTL_DAYS * 86400)
                store["tokens"][th] = {"user": cfg.APP_USER, "exp": exp, "created": _now_ts()}
                _save_auth_store(cfg, store)
                _set_query_token(cfg, tok)
            else:
                _set_query_token(cfg, None)

            st.rerun()
        else:
            st.error("Username / password salah.")

    st.stop()
