import os
import psycopg2
from psycopg2.extras import RealDictCursor

ALLOWED_TABLES = {"dataset_train", "dataset_val", "dataset_test"}

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "mzone_dataset")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASS", os.getenv("DB_PASSWORD", ""))

# cache sederhana untuk info kolom per table
_TABLE_INFO_CACHE = {}


def get_connection():
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASS,
        cursor_factory=RealDictCursor,
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
