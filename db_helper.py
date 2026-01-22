# db_helper.py
import os
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from urllib.parse import urlparse, parse_qs

ALLOWED_TABLES = {"dataset_train", "dataset_val", "dataset_test"}

# cache sederhana untuk info kolom per table
_TABLE_INFO_CACHE = {}

# cache config DB (biar gak parse berulang)
_DB_CFG_CACHE = None


def _get_secret(key: str, default=None):
    """
    Ambil dari st.secrets jika tersedia (Streamlit Cloud),
    fallback ke environment variables (lokal).
    """
    try:
        import streamlit as st
        if key in st.secrets:
            return st.secrets.get(key, default)
    except Exception:
        pass
    return os.getenv(key, default)


def _load_db_cfg() -> dict:
    """
    Return dict config:
      host, port, dbname, user, password, sslmode, connect_timeout
    Support DATABASE_URL / DB_URL.
    """
    global _DB_CFG_CACHE
    if _DB_CFG_CACHE is not None:
        return _DB_CFG_CACHE

    # 1) DATABASE_URL (paling enak untuk deploy)
    db_url = _get_secret("DATABASE_URL", None) or _get_secret("DB_URL", None)
    if db_url:
        u = urlparse(db_url)
        q = parse_qs(u.query or "")

        # sslmode dari query url kalau ada, else dari secrets/env, else require (umumnya cloud butuh)
        sslmode = (q.get("sslmode", [None])[0] or _get_secret("DB_SSLMODE", None) or "require")

        cfg = {
            "host": u.hostname or "",
            "port": int(u.port or 5432),
            "dbname": (u.path or "").lstrip("/") or "",
            "user": u.username or "",
            "password": u.password or "",
            "sslmode": sslmode,
            "connect_timeout": int(_get_secret("DB_CONNECT_TIMEOUT", "10")),
        }
        _DB_CFG_CACHE = cfg
        return cfg

    # 2) Split fields
    host = _get_secret("DB_HOST", "localhost")
    port = int(_get_secret("DB_PORT", "5432"))
    dbname = _get_secret("DB_NAME", "mzone_dataset")
    user = _get_secret("DB_USER", "postgres")

    # Support DB_PASSWORD / DB_PASS
    password = _get_secret("DB_PASSWORD", None)
    if password is None:
        password = _get_secret("DB_PASS", "")

    # SSL default "prefer" biar aman buat lokal (SSL kalau ada)
    sslmode = _get_secret("DB_SSLMODE", "prefer")
    connect_timeout = int(_get_secret("DB_CONNECT_TIMEOUT", "10"))

    cfg = {
        "host": host,
        "port": port,
        "dbname": dbname,
        "user": user,
        "password": password,
        "sslmode": sslmode,
        "connect_timeout": connect_timeout,
    }
    _DB_CFG_CACHE = cfg
    return cfg


def get_connection():
    cfg = _load_db_cfg()

    # Validasi biar error deploy lebih jelas
    missing = [k for k in ["host", "dbname", "user", "password"] if not cfg.get(k)]
    if missing:
        raise RuntimeError(
            f"DB config missing {missing}. "
            f"Isi Secrets/ENV: DB_HOST, DB_NAME, DB_USER, DB_PASSWORD (atau DATABASE_URL)."
        )

    return psycopg2.connect(
        host=cfg["host"],
        port=cfg["port"],
        dbname=cfg["dbname"],
        user=cfg["user"],
        password=cfg["password"],
        sslmode=cfg.get("sslmode", "prefer"),
        connect_timeout=cfg.get("connect_timeout", 10),
        cursor_factory=RealDictCursor,
        application_name="mzone-dataset-review",
    )


def _ensure_table(table_name: str) -> str:
    t = (table_name or "").strip()
    if t not in ALLOWED_TABLES:
        raise ValueError(f"Invalid table: {t}. Allowed: {sorted(ALLOWED_TABLES)}")
    return t


def get_table_info(table_name: str) -> dict:
    """
    Return dict:
      {
        "columns": set([...]),
        "types": {col: {"data_type": ..., "udt_name": ...}}
      }
    Cached per table.
    """
    t = _ensure_table(table_name)
    if t in _TABLE_INFO_CACHE:
        return _TABLE_INFO_CACHE[t]

    sql = """
        SELECT column_name, data_type, udt_name
        FROM information_schema.columns
        WHERE table_schema='public' AND table_name=%s
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (t,))
            rows = cur.fetchall()

    cols = set()
    types = {}
    for r in rows:
        cn = r["column_name"]
        cols.add(cn)
        types[cn] = {"data_type": r["data_type"], "udt_name": r["udt_name"]}

    info = {"columns": cols, "types": types}
    _TABLE_INFO_CACHE[t] = info
    return info


def _events_is_array(table_name: str) -> bool:
    info = get_table_info(table_name)
    if "events" not in info["columns"]:
        return False
    tinfo = info["types"].get("events", {})
    # Postgres text[] biasanya udt_name = _text, data_type = ARRAY
    return (tinfo.get("data_type") == "ARRAY") or (tinfo.get("udt_name") in {"_text"})


def _normalize_events_from_db(table_name: str, ev):
    """Return list[str] always."""
    if ev is None:
        return []
    if isinstance(ev, (list, tuple)):
        return [str(x) for x in ev if str(x).strip()]
    # kalau events disimpan sebagai string "A|B|C"
    if isinstance(ev, str):
        parts = [p.strip() for p in ev.split("|") if p.strip()]
        return parts
    return []


def _normalize_events_for_db(table_name: str, events):
    """Return value compatible with DB column type."""
    if _events_is_array(table_name):
        if events is None:
            return []
        if isinstance(events, (list, tuple)):
            return [str(x) for x in events if str(x).strip()]
        if isinstance(events, str):
            return [p.strip() for p in events.split("|") if p.strip()]
        return []
    else:
        # string
        if events is None:
            return ""
        if isinstance(events, str):
            return events.strip()
        if isinstance(events, (list, tuple)):
            return "|".join([str(x).strip() for x in events if str(x).strip()])
        return ""


def _build_where(table_name: str, intent=None, urgency=None, event=None, keyword=None, reviewed=None):
    """
    reviewed:
      None -> no filter
      True -> only reviewed
      False -> only unreviewed
    """
    info = get_table_info(table_name)
    cols = info["columns"]

    where = []
    params = []

    if intent:
        where.append("intent = %s")
        params.append(intent)

    if urgency:
        where.append("urgency = %s")
        params.append(urgency)

    if keyword:
        where.append("text ILIKE %s")
        params.append(f"%{keyword}%")

    if reviewed is not None and "reviewed" in cols:
        where.append("reviewed = %s")
        params.append(bool(reviewed))

    if event:
        # events array vs string
        if "events" in cols and _events_is_array(table_name):
            where.append("events @> %s::text[]")
            params.append([event])
        elif "events" in cols:
            # string fallback
            where.append("events ILIKE %s")
            params.append(f"%{event}%")

    return where, params


def count_dataset(table_name: str, intent=None, urgency=None, event=None, keyword=None, reviewed=None) -> int:
    t = _ensure_table(table_name)
    where, params = _build_where(t, intent=intent, urgency=urgency, event=event, keyword=keyword, reviewed=reviewed)

    sql = f"SELECT COUNT(*) AS c FROM {t}"
    if where:
        sql += " WHERE " + " AND ".join(where)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, tuple(params))
            r = cur.fetchone()
            return int(r["c"])


def query_dataset(table_name: str, intent=None, urgency=None, event=None, keyword=None, reviewed=None, limit=50, offset=0):
    """
    Return list of dict rows; events normalized to list[str].
    """
    t = _ensure_table(table_name)
    info = get_table_info(t)
    cols = info["columns"]

    select_cols = ["id", "text", "intent", "urgency", "events"]
    if "reviewed" in cols:
        select_cols.append("reviewed")
    if "note" in cols:
        select_cols.append("note")

    where, params = _build_where(t, intent=intent, urgency=urgency, event=event, keyword=keyword, reviewed=reviewed)

    sql = f"SELECT {', '.join(select_cols)} FROM {t}"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY id ASC LIMIT %s OFFSET %s"
    params.extend([int(limit), int(offset)])

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, tuple(params))
            rows = cur.fetchall()

    out = []
    for r in rows:
        rr = dict(r)
        rr["events"] = _normalize_events_from_db(t, rr.get("events"))
        out.append(rr)
    return out


def get_row_by_id(table_name: str, record_id: int):
    t = _ensure_table(table_name)
    info = get_table_info(t)
    cols = info["columns"]

    select_cols = ["id", "text", "intent", "urgency", "events"]
    if "reviewed" in cols:
        select_cols.append("reviewed")
    if "note" in cols:
        select_cols.append("note")

    sql = f"SELECT {', '.join(select_cols)} FROM {t} WHERE id = %s"
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (int(record_id),))
            r = cur.fetchone()
            if not r:
                return None
            rr = dict(r)
            rr["events"] = _normalize_events_from_db(t, rr.get("events"))
            return rr


def get_adjacent_id(table_name: str, current_id: int, direction: str, intent=None, urgency=None, event=None, keyword=None, reviewed=None):
    """
    direction: "next" or "prev"
    """
    t = _ensure_table(table_name)
    where, params = _build_where(t, intent=intent, urgency=urgency, event=event, keyword=keyword, reviewed=reviewed)

    if direction == "next":
        where.append("id > %s")
        params.append(int(current_id))
        order = "ASC"
    else:
        where.append("id < %s")
        params.append(int(current_id))
        order = "DESC"

    sql = f"SELECT id FROM {t}"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += f" ORDER BY id {order} LIMIT 1"

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, tuple(params))
            r = cur.fetchone()
            return int(r["id"]) if r else None


def update_dataset_row(table_name: str, record_id: int, text=None, intent=None, urgency=None, events=None, reviewed=None, note=None):
    """
    Update only provided fields. Compatible with events array or string.
    """
    t = _ensure_table(table_name)
    info = get_table_info(t)
    cols = info["columns"]

    fields = []
    params = []

    if text is not None and "text" in cols:
        fields.append("text = %s")
        params.append(str(text))

    if intent is not None and "intent" in cols:
        fields.append("intent = %s")
        params.append(str(intent))

    if urgency is not None and "urgency" in cols:
        fields.append("urgency = %s")
        params.append(str(urgency))

    if events is not None and "events" in cols:
        fields.append("events = %s")
        params.append(_normalize_events_for_db(t, events))

    if reviewed is not None and "reviewed" in cols:
        fields.append("reviewed = %s")
        params.append(bool(reviewed))

    if note is not None and "note" in cols:
        fields.append("note = %s")
        params.append(str(note))

    if not fields:
        return False

    sql = f"UPDATE {t} SET {', '.join(fields)} WHERE id = %s"
    params.append(int(record_id))

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, tuple(params))
        conn.commit()
    return True
