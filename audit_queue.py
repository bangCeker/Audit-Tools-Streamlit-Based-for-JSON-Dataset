# python audit_queue.py --input "D:\...\train.jsonl" --val "D:\...\val.jsonl" --out-queue "D:\...\review_queue.csv"


# audit_queue.py
import argparse
import csv
import hashlib
import json
import os
import re
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime

# =====================
# LABEL SPACE (EDIT DI SINI)
# =====================
INTENT = ["SOS", "SOS_POSSIBLE", "NON_SOS"]
URGENCY = ["HIGH", "MEDIUM", "LOW"]
EVENTS = [
    "INJURY_MEDICAL",
    "TRAPPED_LOST",
    "COLLISION_VEHICLE",
    "FIRE_EXPLOSION",
    "HAZMAT_RELEASE",
    "GROUND_FAILURE",
    "ELECTRICAL",
    "SECURITY_ASSAULT",
]

# =====================
# RULES (triage / flag) — tidak auto-ubah, hanya kasih "reason + suggestion"
# =====================
RULES = [
    {
        "name": "kw_collision_missing_event",
        "regex": r"\b(tabrak|menabrak|tabrakan|tertabrak|nabrak|bentur|ketabrak|collision)\b",
        "suggest_events": ["COLLISION_VEHICLE"],
        "min_intent": "SOS_POSSIBLE",
        "min_urgency": "MEDIUM",
    },
    {
        "name": "kw_injury_missing_event",
        "regex": r"\b(berdarah|luka|patah|cedera|trauma|memar|pingsan|patah tulang)\b",
        "suggest_events": ["INJURY_MEDICAL"],
        "min_intent": "SOS",
        "min_urgency": "HIGH",
    },
    {
        "name": "kw_trapped_missing_event",
        "regex": r"\b(terjepit|terperangkap|terjebak|ketindih|keblender|kejit|kejepit)\b",
        "suggest_events": ["TRAPPED_LOST"],
        "min_intent": "SOS",
        "min_urgency": "HIGH",
    },
    {
        "name": "kw_hazmat_missing_event",
        "regex": r"\b(h2s|hidrogen sulfida|gas beracun|sesak nafas|sesak napas|keracunan|asphyx|asfiksia)\b",
        "suggest_events": ["HAZMAT_RELEASE"],
        "min_intent": "SOS",
        "min_urgency": "HIGH",
    },
    {
        "name": "kw_fire_missing_event",
        "regex": r"\b(kebakaran|api|asap tebal|terbakar|meledak|ledakan|fire)\b",
        "suggest_events": ["FIRE_EXPLOSION"],
        "min_intent": "SOS",
        "min_urgency": "HIGH",
    },
    {
        "name": "kw_electrical_missing_event",
        "regex": r"\b(korslet|arus pendek|tersengat|kesetrum|listrik|sparking)\b",
        "suggest_events": ["ELECTRICAL"],
        "min_intent": "SOS_POSSIBLE",
        "min_urgency": "MEDIUM",
    },
    {
        "name": "kw_ground_failure_missing_event",
        "regex": r"\b(longsor|ambrol|runtuh|retak tanah|highwall|lowwall|slip)\b",
        "suggest_events": ["GROUND_FAILURE"],
        "min_intent": "SOS_POSSIBLE",
        "min_urgency": "MEDIUM",
    },
    {
        "name": "kw_security_missing_event",
        "regex": r"\b(pemukulan|penyerangan|perkelahian|begal|assault|ancam|mengancam)\b",
        "suggest_events": ["SECURITY_ASSAULT"],
        "min_intent": "SOS",
        "min_urgency": "HIGH",
    },
    {
        "name": "kw_emergency_word_but_non_sos",
        "regex": r"\b(emergency|darurat|tolong|urgent|segera)\b",
        "suggest_events": [],
        "min_intent": "SOS_POSSIBLE",
        "min_urgency": "MEDIUM",
    },
]

# event berat → biasanya butuh urgency min tertentu
HEAVY_EVENTS_MIN_URGENCY = {
    "FIRE_EXPLOSION": "HIGH",
    "HAZMAT_RELEASE": "HIGH",
    "INJURY_MEDICAL": "HIGH",  # bisa kamu naikkan ke HIGH kalau mau
    "COLLISION_VEHICLE": "HIGH",
}

# =====================
# Utils
# =====================
def normalize_text(t: str) -> str:
    t = t or ""
    t = unicodedata.normalize("NFKC", t)
    t = t.lower().strip()
    t = re.sub(r"\s+", " ", t).strip()
    return t

def sha1_hex(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()

def order_rank(label: str, space: list) -> int:
    # semakin kecil semakin "tinggi prioritas"
    try:
        return space.index(label)
    except ValueError:
        return 10**9

def max_severity(a: str, b: str, space: list) -> str:
    # pilih yang lebih "tinggi"
    return a if order_rank(a, space) < order_rank(b, space) else b

def min_required(label: str, min_label: str, space: list) -> bool:
    # True kalau label sudah >= min_label (dalam severity)
    return order_rank(label, space) <= order_rank(min_label, space)

def safe_list(x):
    if x is None:
        return []
    if isinstance(x, list):
        return x
    return []

def validate_row(r: dict):
    problems = []

    if "text" not in r or not isinstance(r.get("text"), str) or not r.get("text").strip():
        problems.append("missing_or_empty_text")

    it = r.get("intent")
    if it not in INTENT:
        problems.append("invalid_intent")

    urg = r.get("urgency")
    if urg not in URGENCY:
        problems.append("invalid_urgency")

    ev = safe_list(r.get("events", []))
    bad_ev = [e for e in ev if e not in EVENTS]
    if bad_ev:
        problems.append("invalid_events")

    return problems

def parse_jsonl(path: str):
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
                if not isinstance(r, dict):
                    continue
                r["_idx"] = i
                rows.append(r)
            except Exception:
                # skip broken line
                continue
    return rows

def stringify_events(ev_list):
    ev_list = safe_list(ev_list)
    # stable order
    ev_list = [e for e in EVENTS if e in ev_list]
    return "|".join(ev_list)

def suggest_from_rules(text_norm: str, cur_intent: str, cur_urg: str, cur_events: list):
    reasons = []
    hits = []
    sug_intent = None
    sug_urg = None
    sug_events = set()

    cur_events_set = set(safe_list(cur_events))

    for rule in RULES:
        pat = re.search(rule["regex"], text_norm, flags=re.I)
        if not pat:
            continue

        reasons.append(rule["name"])
        hits.append(rule["regex"])

        # suggest events if missing
        for e in rule.get("suggest_events", []):
            if e not in cur_events_set:
                sug_events.add(e)

        # suggest intent/urgency min
        min_it = rule.get("min_intent")
        if min_it and cur_intent in INTENT:
            if not min_required(cur_intent, min_it, INTENT):
                sug_intent = max_severity(sug_intent or cur_intent, min_it, INTENT)

        min_urg = rule.get("min_urgency")
        if min_urg and cur_urg in URGENCY:
            if not min_required(cur_urg, min_urg, URGENCY):
                sug_urg = max_severity(sug_urg or cur_urg, min_urg, URGENCY)

    # heavy event → urgency min
    for e in cur_events_set:
        min_urg = HEAVY_EVENTS_MIN_URGENCY.get(e)
        if min_urg and cur_urg in URGENCY:
            if not min_required(cur_urg, min_urg, URGENCY):
                reasons.append(f"heavy_event_low_urgency:{e}")
                sug_urg = max_severity(sug_urg or cur_urg, min_urg, URGENCY)

    # emergency-ish intent rules
    if cur_intent == "NON_SOS":
        # kalau ada heavy event tapi NON_SOS → flag
        if any(e in {"FIRE_EXPLOSION", "HAZMAT_RELEASE", "INJURY_MEDICAL", "TRAPPED_LOST"} for e in cur_events_set):
            reasons.append("non_sos_with_heavy_event")
            sug_intent = "SOS_POSSIBLE"

    return reasons, hits, sug_intent, sug_urg, sorted(list(sug_events), key=lambda x: EVENTS.index(x))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="path jsonl (train/val)")
    ap.add_argument("--val", default=None, help="optional: path val jsonl for leakage check")
    ap.add_argument("--out-queue", required=True, help="output review queue csv")
    ap.add_argument("--out-stats", default=None, help="optional: output stats json")
    ap.add_argument("--max-queue", type=int, default=0, help="0 = no limit, else cap")
    args = ap.parse_args()

    rows = parse_jsonl(args.input)
    val_hashes = set()
    if args.val and os.path.exists(args.val):
        val_rows = parse_jsonl(args.val)
        for vr in val_rows:
            t = normalize_text(vr.get("text", ""))
            if t:
                val_hashes.add(sha1_hex(t))

    # duplicates inside file
    hash_to_idxs = defaultdict(list)
    for r in rows:
        t = normalize_text(r.get("text", ""))
        h = sha1_hex(t) if t else ""
        r["_text_norm"] = t
        r["_id"] = r.get("id") or (h if h else f"row_{r.get('_idx')}")
        r["_hash"] = h
        if h:
            hash_to_idxs[h].append(r["_idx"])

    dup_hashes = {h for h, idxs in hash_to_idxs.items() if len(idxs) > 1}

    # stats
    cnt_int = Counter()
    cnt_urg = Counter()
    cnt_evt = Counter()
    problem_cnt = Counter()

    queue = []
    for r in rows:
        idx = r["_idx"]
        text = r.get("text", "")
        tnorm = r["_text_norm"]
        rid = r["_id"]
        it = r.get("intent", "")
        urg = r.get("urgency", "")
        ev = safe_list(r.get("events", []))

        if it in INTENT:
            cnt_int[it] += 1
        if urg in URGENCY:
            cnt_urg[urg] += 1
        for e in ev:
            if e in EVENTS:
                cnt_evt[e] += 1

        problems = validate_row(r)
        for p in problems:
            problem_cnt[p] += 1

        reasons = []
        hits = []
        sug_intent = None
        sug_urg = None
        sug_events = []

        # basic invalid label flags
        if problems:
            reasons.extend([f"data_problem:{p}" for p in problems])

        # duplicate flags
        if r["_hash"] and r["_hash"] in dup_hashes:
            reasons.append("duplicate_text_in_split")

        # leakage flags
        if args.val and r["_hash"] and (r["_hash"] in val_hashes) and (os.path.abspath(args.input) != os.path.abspath(args.val)):
            reasons.append("train_val_text_leakage")

        # rules suggestions
        r2, h2, si, su, se = suggest_from_rules(tnorm, it if it in INTENT else "", urg if urg in URGENCY else "", ev)
        reasons.extend(r2)
        hits.extend(h2)
        sug_intent = si
        sug_urg = su
        sug_events = se

        # only enqueue if something suspicious
        if reasons:
            queue.append({
                "idx": idx,
                "id": rid,
                "text": text,
                "intent": it,
                "urgency": urg,
                "events": stringify_events(ev),
                "reasons": "|".join(sorted(set(reasons))),
                "suggest_intent": sug_intent or "",
                "suggest_urgency": sug_urg or "",
                "suggest_events": "|".join(sug_events) if sug_events else "",
                "keyword_hits": "|".join(sorted(set(hits))) if hits else "",
            })

    # prioritize queue: leakage/duplicate/problems first
    def score_row(qr):
        s = 0
        rs = qr["reasons"]
        if "train_val_text_leakage" in rs:
            s += 100
        if "duplicate_text_in_split" in rs:
            s += 50
        if "data_problem:" in rs:
            s += 80
        # heavy mislabels
        if "non_sos_with_heavy_event" in rs:
            s += 30
        if "heavy_event_low_urgency" in rs:
            s += 20
        # keyword missing event
        if "kw_" in rs:
            s += 10
        return -s  # smaller = higher priority in sort

    queue.sort(key=score_row)

    if args.max_queue and args.max_queue > 0:
        queue = queue[:args.max_queue]

    # write queue csv
    os.makedirs(os.path.dirname(args.out_queue) or ".", exist_ok=True)
    with open(args.out_queue, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "idx","id","text","intent","urgency","events",
                "reasons","suggest_intent","suggest_urgency","suggest_events","keyword_hits"
            ]
        )
        w.writeheader()
        for row in queue:
            w.writerow(row)

    print(f"[OK] Wrote queue: {args.out_queue} (items={len(queue)})")

    # optional stats json
    if args.out_stats:
        os.makedirs(os.path.dirname(args.out_stats) or ".", exist_ok=True)
        stats = {
            "created_at": datetime.utcnow().isoformat() + "Z",
            "input": args.input,
            "n_rows": len(rows),
            "intent_counts": dict(cnt_int),
            "urgency_counts": dict(cnt_urg),
            "event_counts": dict(cnt_evt),
            "problem_counts": dict(problem_cnt),
            "queue_size": len(queue),
        }
        with open(args.out_stats, "w", encoding="utf-8") as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
        print(f"[OK] Wrote stats: {args.out_stats}")

if __name__ == "__main__":
    main()
