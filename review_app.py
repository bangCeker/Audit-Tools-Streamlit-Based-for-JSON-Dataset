# # review_app.py
# import json
# import os
# import re
# import hashlib
# import unicodedata
# from datetime import datetime

# import pandas as pd
# import streamlit as st

# # =====================
# # LABEL SPACE (HARUS sama dengan training)
# # =====================
# INTENT = ["SOS", "SOS_POSSIBLE", "NON_SOS"]
# URGENCY = ["HIGH", "MEDIUM", "LOW"]
# EVENTS = [
#     "INJURY_MEDICAL",
#     "TRAPPED_LOST",
#     "COLLISION_VEHICLE",
#     "FIRE_EXPLOSION",
#     "HAZMAT_RELEASE",
#     "GROUND_FAILURE",
#     "ELECTRICAL",
#     "SECURITY_ASSAULT",
# ]

# # highlight keyword (visual doang)
# HILITE_PATTERNS = [
#     r"\b(tabrak|menabrak|tabrakan|tertabrak|nabrak|bentur|ketabrak|collision)\b",
#     r"\b(berdarah|luka|patah|cedera|trauma|memar|pingsan)\b",
#     r"\b(terjepit|terperangkap|terjebak|ketindih)\b",
#     r"\b(h2s|hidrogen sulfida|gas beracun|sesak nafas|sesak napas|asfiksia)\b",
#     r"\b(kebakaran|api|asap|terbakar|meledak|ledakan|fire)\b",
#     r"\b(korslet|arus pendek|kesetrum|listrik|sparking)\b",
#     r"\b(longsor|ambrol|runtuh|retak tanah|highwall|lowwall|slip)\b",
#     r"\b(emergency|darurat|tolong|urgent|segera)\b",
# ]

# # =====================
# # Utils
# # =====================
# def normalize_text(t: str) -> str:
#     t = t or ""
#     t = unicodedata.normalize("NFKC", t).lower().strip()
#     t = re.sub(r"\s+", " ", t).strip()
#     return t

# def sha1_hex(s: str) -> str:
#     return hashlib.sha1(s.encode("utf-8")).hexdigest()

# def safe_list(x):
#     if x is None:
#         return []
#     if isinstance(x, list):
#         return x
#     return []

# def stable_events(ev_list):
#     ev_list = safe_list(ev_list)
#     return [e for e in EVENTS if e in ev_list]

# def parse_events_str(s: str):
#     if not s or not isinstance(s, str):
#         return []
#     parts = [p.strip() for p in s.split("|") if p.strip()]
#     return [e for e in EVENTS if e in parts]

# def highlight_text(text: str):
#     esc = (
#         (text or "")
#         .replace("&", "&amp;")
#         .replace("<", "&lt;")
#         .replace(">", "&gt;")
#     )
#     out = esc
#     for pat in HILITE_PATTERNS:
#         out = re.sub(pat, lambda m: f"<mark>{m.group(0)}</mark>", out, flags=re.I)
#     return out

# @st.cache_data(show_spinner=False)
# def load_jsonl(path: str):
#     rows = []
#     with open(path, "r", encoding="utf-8") as f:
#         for i, line in enumerate(f):
#             line = line.strip()
#             if not line:
#                 continue
#             r = json.loads(line)
#             if not isinstance(r, dict):
#                 continue
#             r["_idx"] = i
#             tnorm = normalize_text(r.get("text", ""))
#             r["_id"] = r.get("id") or (sha1_hex(tnorm) if tnorm else f"row_{i}")
#             rows.append(r)
#     id2pos = {r["_id"]: k for k, r in enumerate(rows)}
#     return rows, id2pos

# @st.cache_data(show_spinner=False)
# def load_queue_csv(path: str):
#     df = pd.read_csv(path)
#     for c in [
#         "idx","id","text","intent","urgency","events",
#         "reasons","suggest_intent","suggest_urgency","suggest_events","keyword_hits"
#     ]:
#         if c not in df.columns:
#             df[c] = ""
#     df["id"] = df["id"].astype(str)
#     return df

# def append_log(log_path: str, rec: dict):
#     os.makedirs(os.path.dirname(log_path) or ".", exist_ok=True)
#     file_exists = os.path.exists(log_path)
#     cols = [
#         "ts","id","idx",
#         "old_intent","new_intent",
#         "old_urgency","new_urgency",
#         "old_events","new_events",
#         "reasons","note"
#     ]
#     line = {k: rec.get(k, "") for k in cols}
#     with open(log_path, "a", encoding="utf-8") as f:
#         if not file_exists:
#             f.write("\t".join(cols) + "\n")
#         f.write("\t".join(str(line[k]) for k in cols) + "\n")

# def write_jsonl(path: str, rows: list):
#     os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
#     with open(path, "w", encoding="utf-8") as f:
#         for r in rows:
#             rr = dict(r)
#             rr.pop("_idx", None)
#             rr.pop("_id", None)
#             rr["events"] = stable_events(rr.get("events", []))
#             f.write(json.dumps(rr, ensure_ascii=False) + "\n")

# # =====================
# # Streamlit UI
# # =====================
# st.set_page_config(page_title="MZone Dataset Review", layout="wide")
# st.title("MZone Dataset Review — Quick Buttons + Apply Suggestions + Batch Editor")

# with st.sidebar:
#     st.header("Paths")
#     data_path = st.text_input("Dataset JSONL path", value=r"D:\MzoneDeploy\mzone-staging\dataset\splits_v5_audit\train.jsonl")
#     queue_path = st.text_input("Queue CSV path (dari audit_queue.py)", value=r"D:\MzoneDeploy\mzone-staging\dataset\splits_v5_audit\train_review_queue.csv")
#     out_fixed_path = st.text_input("Output fixed JSONL", value=r"D:\MzoneDeploy\mzone-staging\dataset\splits_v5_audit\audit_train.jsonl")
#     log_path = st.text_input("Change log TSV", value=r"D:\MzoneDeploy\mzone-staging\dataset\splits_v5_audit\changes_log.tsv")

#     st.divider()
#     st.header("Mode")
#     mode = st.radio("Pilih mode", ["Queue Review", "Search/Filter"], index=0)

#     st.divider()
#     st.header("Quick filters (Queue)")
#     reason_filter = st.text_input("Filter reasons contains (optional)", value="")
#     show_only_with_suggestions = st.checkbox("Hanya yang ada suggestion", value=False)

#     st.divider()
#     st.header("Batch mode")
#     batch_mode = st.checkbox("Aktifkan Batch Editor", value=True)
#     batch_size = st.slider("Batch size", min_value=10, max_value=100, value=25, step=5)

#     st.divider()
#     st.header("Search/Filter (kalau mode Search)")
#     f_keyword = st.text_input("Keyword/regex", value="")
#     f_event = st.selectbox("Event", ["(any)"] + EVENTS, index=0)
#     f_urg = st.selectbox("Urgency", ["(any)"] + URGENCY, index=0)
#     f_int = st.selectbox("Intent", ["(any)"] + INTENT, index=0)

# # Load dataset
# if not data_path or not os.path.exists(data_path):
#     st.error("Dataset path tidak valid / file tidak ditemukan.")
#     st.stop()

# rows, id2pos = load_jsonl(data_path)

# # Build item list
# queue_df = None
# item_ids = []

# if mode == "Queue Review":
#     if queue_path and os.path.exists(queue_path):
#         queue_df = load_queue_csv(queue_path)

#         df = queue_df.copy()
#         if reason_filter.strip():
#             df = df[df["reasons"].astype(str).str.contains(reason_filter.strip(), case=False, na=False)]
#         if show_only_with_suggestions:
#             df = df[
#                 (df["suggest_intent"].astype(str).str.len() > 0) |
#                 (df["suggest_urgency"].astype(str).str.len() > 0) |
#                 (df["suggest_events"].astype(str).str.len() > 0)
#             ]
#         item_ids = [str(x) for x in df["id"].tolist() if str(x) in id2pos]
#         queue_df = df.reset_index(drop=True)
#     else:
#         st.warning("Queue CSV tidak ditemukan. Jalankan audit_queue.py dulu atau pakai mode Search.")
# else:
#     kw = f_keyword.strip()
#     pat = None
#     if kw:
#         try:
#             pat = re.compile(kw, flags=re.I)
#         except Exception:
#             pat = None

#     for r in rows:
#         ok = True
#         if f_event != "(any)":
#             ok = ok and (f_event in safe_list(r.get("events", [])))
#         if f_urg != "(any)":
#             ok = ok and (r.get("urgency") == f_urg)
#         if f_int != "(any)":
#             ok = ok and (r.get("intent") == f_int)
#         if pat is not None:
#             ok = ok and bool(pat.search(r.get("text", "")))
#         if ok:
#             item_ids.append(r["_id"])

# if not item_ids:
#     st.info("Tidak ada item untuk direview (cek mode/filters).")
#     st.stop()

# # session state
# if "cursor" not in st.session_state:
#     st.session_state.cursor = 0
# if "history" not in st.session_state:
#     st.session_state.history = []  # undo stack
# if "page" not in st.session_state:
#     st.session_state.page = 0

# def get_queue_row(cur_id: str):
#     if queue_df is None:
#         return None
#     q = queue_df[queue_df["id"].astype(str) == str(cur_id)]
#     if len(q) == 0:
#         return None
#     return q.iloc[0].to_dict()

# def apply_suggestion_to_state(qrow, replace_events=False):
#     if not qrow:
#         return
#     sug_i = str(qrow.get("suggest_intent", "") or "").strip()
#     sug_u = str(qrow.get("suggest_urgency", "") or "").strip()
#     sug_e = parse_events_str(str(qrow.get("suggest_events", "") or ""))

#     if sug_i in INTENT:
#         st.session_state.edit_intent = sug_i
#     if sug_u in URGENCY:
#         st.session_state.edit_urgency = sug_u

#     if sug_e:
#         if replace_events:
#             st.session_state.edit_events = stable_events(sug_e)
#         else:
#             cur = set(st.session_state.edit_events)
#             cur |= set(sug_e)
#             st.session_state.edit_events = stable_events(list(cur))

# def save_change(cur_id: str, note: str, reasons: str = ""):
#     pos = id2pos[cur_id]
#     r = rows[pos]

#     old_intent = r.get("intent", "")
#     old_urg = r.get("urgency", "")
#     old_ev = stable_events(r.get("events", []))

#     new_intent = st.session_state.edit_intent
#     new_urg = st.session_state.edit_urgency
#     new_ev = stable_events(st.session_state.edit_events)

#     changed = (old_intent != new_intent) or (old_urg != new_urg) or (old_ev != new_ev)
#     if not changed:
#         return False

#     st.session_state.history.append({
#         "id": cur_id, "pos": pos,
#         "old_intent": old_intent, "old_urgency": old_urg, "old_events": old_ev
#     })

#     r["intent"] = new_intent
#     r["urgency"] = new_urg
#     r["events"] = new_ev

#     append_log(log_path, {
#         "ts": datetime.now().isoformat(timespec="seconds"),
#         "id": cur_id,
#         "idx": r.get("_idx"),
#         "old_intent": old_intent, "new_intent": new_intent,
#         "old_urgency": old_urg, "new_urgency": new_urg,
#         "old_events": "|".join(old_ev), "new_events": "|".join(new_ev),
#         "reasons": reasons or "",
#         "note": note or "",
#     })
#     return True

# def undo_last():
#     if not st.session_state.history:
#         return False
#     last = st.session_state.history.pop()
#     pos = last["pos"]
#     rows[pos]["intent"] = last["old_intent"]
#     rows[pos]["urgency"] = last["old_urgency"]
#     rows[pos]["events"] = last["old_events"]
#     return True

# def go_next_single():
#     st.session_state.cursor = min(st.session_state.cursor + 1, len(item_ids) - 1)

# def go_prev_single():
#     st.session_state.cursor = max(st.session_state.cursor - 1, 0)

# # =====================
# # BATCH MODE
# # =====================
# if batch_mode:
#     total = len(item_ids)
#     pages = (total + batch_size - 1) // batch_size
#     st.session_state.page = max(0, min(st.session_state.page, pages - 1))

#     start = st.session_state.page * batch_size
#     end = min(start + batch_size, total)
#     batch_ids = item_ids[start:end]

#     st.subheader(f"Batch Editor ({start+1}-{end} dari {total})")

#     # Build batch DF (with one bool column per event)
#     data = []
#     for cid in batch_ids:
#         r = rows[id2pos[cid]]
#         ev = set(stable_events(r.get("events", [])))
#         qrow = get_queue_row(cid) if mode == "Queue Review" else None

#         row = {
#             "id": cid,
#             "idx": int(r.get("_idx", -1)),
#             "text": (r.get("text", "") or "")[:140],
#             "intent": r.get("intent", ""),
#             "urgency": r.get("urgency", ""),
#             "reasons": (qrow.get("reasons","") if qrow else ""),
#             "suggest_intent": (qrow.get("suggest_intent","") if qrow else ""),
#             "suggest_urgency": (qrow.get("suggest_urgency","") if qrow else ""),
#             "suggest_events": (qrow.get("suggest_events","") if qrow else ""),
#         }
#         for e in EVENTS:
#             row[f"EV_{e}"] = (e in ev)
#         data.append(row)

#     batch_df = pd.DataFrame(data)

#     # column config for better click-click
#     col_cfg = {
#         "intent": st.column_config.SelectboxColumn("intent", options=INTENT, required=False),
#         "urgency": st.column_config.SelectboxColumn("urgency", options=URGENCY, required=False),
#         "text": st.column_config.TextColumn("text", width="large"),
#         "reasons": st.column_config.TextColumn("reasons", width="medium"),
#         "suggest_intent": st.column_config.TextColumn("suggest_intent", width="small"),
#         "suggest_urgency": st.column_config.TextColumn("suggest_urgency", width="small"),
#         "suggest_events": st.column_config.TextColumn("suggest_events", width="small"),
#     }
#     for e in EVENTS:
#         col_cfg[f"EV_{e}"] = st.column_config.CheckboxColumn(e, width="small")

#     # keep editor state across reruns
#     editor_key = f"batch_editor_page_{st.session_state.page}"
#     edited = st.data_editor(
#         batch_df,
#         key=editor_key,
#         use_container_width=True,
#         hide_index=True,
#         column_config=col_cfg,
#         disabled=["id","idx","reasons","suggest_intent","suggest_urgency","suggest_events"],
#     )

#     c1, c2, c3, c4, c5 = st.columns([1,1,1,1,2])

#     if c1.button("⬅ Prev page", disabled=(st.session_state.page == 0)):
#         st.session_state.page -= 1
#         st.rerun()

#     if c2.button("Next page ➡", disabled=(st.session_state.page >= pages - 1)):
#         st.session_state.page += 1
#         st.rerun()

#     # Apply suggestions to all rows in current batch (Queue mode only)
#     if c3.button("✨ Apply suggestions (batch)", disabled=(mode != "Queue Review" or queue_df is None)):
#         ed = edited.copy()
#         for i in range(len(ed)):
#             sid = str(ed.loc[i, "id"])
#             q = get_queue_row(sid)
#             if not q:
#                 continue
#             si = str(q.get("suggest_intent","") or "").strip()
#             su = str(q.get("suggest_urgency","") or "").strip()
#             se = parse_events_str(str(q.get("suggest_events","") or ""))

#             if si in INTENT:
#                 ed.loc[i, "intent"] = si
#             if su in URGENCY:
#                 ed.loc[i, "urgency"] = su
#             if se:
#                 for e in se:
#                     ed.loc[i, f"EV_{e}"] = True
#         st.session_state[editor_key] = ed  # overwrite editor state
#         st.rerun()

#     # Save batch changes
#     if c4.button("💾 Save batch"):
#         ed = edited.copy()
#         saved = 0
#         for i in range(len(ed)):
#             cid = str(ed.loc[i, "id"])
#             pos = id2pos[cid]
#             r = rows[pos]

#             old_intent = r.get("intent","")
#             old_urg = r.get("urgency","")
#             old_ev = stable_events(r.get("events", []))

#             new_intent = str(ed.loc[i, "intent"])
#             new_urg = str(ed.loc[i, "urgency"])
#             new_ev = [e for e in EVENTS if bool(ed.loc[i, f"EV_{e}"])]

#             # validate quick (kalau kosong/invalid, skip)
#             if new_intent not in INTENT or new_urg not in URGENCY:
#                 continue

#             changed = (old_intent != new_intent) or (old_urg != new_urg) or (old_ev != new_ev)
#             if not changed:
#                 continue

#             # apply
#             r["intent"] = new_intent
#             r["urgency"] = new_urg
#             r["events"] = stable_events(new_ev)

#             qrow = get_queue_row(cid) if mode == "Queue Review" else None
#             reasons = (qrow.get("reasons","") if qrow else "")

#             append_log(log_path, {
#                 "ts": datetime.now().isoformat(timespec="seconds"),
#                 "id": cid,
#                 "idx": r.get("_idx"),
#                 "old_intent": old_intent, "new_intent": new_intent,
#                 "old_urgency": old_urg, "new_urgency": new_urg,
#                 "old_events": "|".join(old_ev), "new_events": "|".join(new_ev),
#                 "reasons": reasons,
#                 "note": "batch_save",
#             })
#             saved += 1

#         st.success(f"Saved batch changes: {saved} row(s). Log updated: {log_path}")

#     if c5.button("📦 Export fixed JSONL"):
#         write_jsonl(out_fixed_path, rows)
#         st.success(f"Export done ✓ → {out_fixed_path}")
#         st.info(f"Log: {log_path}")

#     st.caption("Tip: batch mode paling cepat. Lakukan Save Batch tiap 1–2 halaman, Export berkala biar aman.")
#     st.stop()

# # =====================
# # SINGLE REVIEW MODE (dengan quick buttons + apply suggestion)
# # =====================
# st.subheader("Single Review (detail)")

# # clamp cursor
# st.session_state.cursor = max(0, min(st.session_state.cursor, len(item_ids) - 1))
# cur_id = item_ids[st.session_state.cursor]
# cur_pos = id2pos[cur_id]
# cur = rows[cur_pos]

# # init edit state when moving to new item
# if st.session_state.get("_cur_loaded_id") != cur_id:
#     st.session_state._cur_loaded_id = cur_id
#     st.session_state.edit_intent = cur.get("intent", INTENT[0]) if cur.get("intent") in INTENT else INTENT[0]
#     st.session_state.edit_urgency = cur.get("urgency", URGENCY[1]) if cur.get("urgency") in URGENCY else URGENCY[1]
#     st.session_state.edit_events = stable_events(cur.get("events", []))

# qrow = get_queue_row(cur_id)

# # header/progress
# colA, colB, colC = st.columns([2, 2, 3])
# with colA:
#     st.metric("Progress", f"{st.session_state.cursor+1}/{len(item_ids)}")
# with colB:
#     st.write(f"**id:** `{cur_id}`")
#     st.write(f"**idx:** `{cur.get('_idx')}`")
# with colC:
#     st.write("**Current labels**")
#     st.write(f"- intent: `{cur.get('intent')}`")
#     st.write(f"- urgency: `{cur.get('urgency')}`")
#     st.write(f"- events: `{', '.join(stable_events(cur.get('events', [])))}`")

# if mode == "Queue Review" and qrow:
#     st.warning(f"**Reasons:** {qrow.get('reasons','')}")
#     sug_i = qrow.get("suggest_intent","")
#     sug_u = qrow.get("suggest_urgency","")
#     sug_e = qrow.get("suggest_events","")
#     if any([str(sug_i).strip(), str(sug_u).strip(), str(sug_e).strip()]):
#         st.info(
#             f"**Suggestions**  \n"
#             f"- intent: `{sug_i or '-'} `  \n"
#             f"- urgency: `{sug_u or '-'} `  \n"
#             f"- events: `{sug_e or '-'} `"
#         )

# # text view
# st.markdown("### Text")
# st.markdown(highlight_text(cur.get("text","")), unsafe_allow_html=True)

# # quick buttons
# st.markdown("### Quick Buttons (1 klik)")
# b1, b2, b3, b4, b5, b6 = st.columns([1,1,1,1,1,1])

# if b1.button("Set SOS"):
#     st.session_state.edit_intent = "SOS"
#     st.rerun()
# if b2.button("Set SOS_POSSIBLE"):
#     st.session_state.edit_intent = "SOS_POSSIBLE"
#     st.rerun()
# if b3.button("Set NON_SOS"):
#     st.session_state.edit_intent = "NON_SOS"
#     st.rerun()

# if b4.button("Set HIGH"):
#     st.session_state.edit_urgency = "HIGH"
#     st.rerun()
# if b5.button("Set MEDIUM"):
#     st.session_state.edit_urgency = "MEDIUM"
#     st.rerun()
# if b6.button("Set LOW"):
#     st.session_state.edit_urgency = "LOW"
#     st.rerun()

# c1, c2, c3, c4, c5, c6 = st.columns([1,1,1,1,1,1])

# def add_event(ev):
#     curset = set(st.session_state.edit_events)
#     curset.add(ev)
#     st.session_state.edit_events = stable_events(list(curset))

# if c1.button("+ COLLISION"):
#     add_event("COLLISION_VEHICLE"); st.rerun()
# if c2.button("+ INJURY"):
#     add_event("INJURY_MEDICAL"); st.rerun()
# if c3.button("+ TRAPPED"):
#     add_event("TRAPPED_LOST"); st.rerun()
# if c4.button("+ FIRE"):
#     add_event("FIRE_EXPLOSION"); st.rerun()
# if c5.button("+ HAZMAT"):
#     add_event("HAZMAT_RELEASE"); st.rerun()
# if c6.button("Clear events"):
#     st.session_state.edit_events = []; st.rerun()

# d1, d2, d3, d4 = st.columns([1,1,1,3])
# replace_events = d1.checkbox("Replace events when applying suggestion", value=False)
# if d2.button("✨ Apply Suggestions", disabled=(mode != "Queue Review" or not qrow)):
#     apply_suggestion_to_state(qrow, replace_events=replace_events)
#     st.rerun()
# if d3.button("↩ Undo"):
#     ok = undo_last()
#     if ok:
#         st.success("Undo ✓")
#     else:
#         st.warning("Tidak ada yang bisa di-undo.")
#     st.rerun()

# # edit form
# st.markdown("### Edit form (klik-klik)")
# with st.form("edit_form", clear_on_submit=False):
#     e1, e2, e3 = st.columns([1, 1, 2])
#     with e1:
#         st.selectbox("Intent", INTENT, key="edit_intent")
#     with e2:
#         st.selectbox("Urgency", URGENCY, key="edit_urgency")
#     with e3:
#         st.multiselect("Events", EVENTS, key="edit_events")

#     note = st.text_input("Note (optional)", value="")
#     f1, f2, f3, f4 = st.columns([1,1,1,1])

#     keep_next = f1.form_submit_button("✅ Keep & Next")
#     save_next = f2.form_submit_button("💾 Save & Next")
#     prev_btn = f3.form_submit_button("⬅ Prev")
#     export_btn = f4.form_submit_button("📦 Export")

# if keep_next:
#     go_next_single()
#     st.rerun()

# if prev_btn:
#     go_prev_single()
#     st.rerun()

# if save_next:
#     reasons = (qrow.get("reasons","") if qrow else "")
#     changed = save_change(cur_id, note=note, reasons=reasons)
#     if changed:
#         st.success("Saved ✓")
#     go_next_single()
#     st.rerun()

# if export_btn:
#     write_jsonl(out_fixed_path, rows)
#     st.success(f"Export done ✓ → {out_fixed_path}")
#     st.info(f"Log: {log_path}")
#     st.stop()

# # navigation
# st.divider()
# n1, n2, n3 = st.columns([1,1,3])
# if n1.button("⬅ Prev"):
#     go_prev_single(); st.rerun()
# if n2.button("Next ➡"):
#     go_next_single(); st.rerun()
# with n3:
#     st.write(f"Undo stack: **{len(st.session_state.history)}**")
#     st.caption("Tip: kalau sudah cepat pakai Batch Mode lagi, Single Mode buat kasus sulit saja.")


# review_app.py
# Streamlit app untuk review + edit dataset JSONL (30k+ rows) dengan 2 UI mode:
# 1) Batch Editor (klik-klik cepat banyak baris)
# 2) Single Review (text kiri wrap, panel kanan vertikal + tombol Next)
#
# Jalankan:
#   streamlit run review_app.py

# review_app.py
import json
import os
import re
import hashlib
import unicodedata
from datetime import datetime

import pandas as pd
import streamlit as st

# =====================
# LABEL SPACE (HARUS sama dengan training)
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

# highlight keyword (visual doang)
HILITE_PATTERNS = [
    r"\b(tabrak|menabrak|tabrakan|tertabrak|nabrak|bentur|ketabrak|collision)\b",
    r"\b(berdarah|luka|patah|cedera|trauma|memar|pingsan)\b",
    r"\b(terjepit|terperangkap|terjebak|ketindih)\b",
    r"\b(h2s|hidrogen sulfida|gas beracun|sesak nafas|sesak napas|asfiksia)\b",
    r"\b(kebakaran|api|asap|terbakar|meledak|ledakan|fire)\b",
    r"\b(korslet|arus pendek|kesetrum|listrik|sparking)\b",
    r"\b(longsor|ambrol|runtuh|retak tanah|highwall|lowwall|slip)\b",
    r"\b(emergency|darurat|tolong|urgent|segera)\b",
]

# =====================
# Utils
# =====================
def normalize_text(t: str) -> str:
    t = t or ""
    t = unicodedata.normalize("NFKC", t).lower().strip()
    t = re.sub(r"\s+", " ", t).strip()
    return t

def sha1_hex(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()

def safe_list(x):
    if x is None:
        return []
    if isinstance(x, list):
        return x
    return []

def stable_events(ev_list):
    ev_list = safe_list(ev_list)
    return [e for e in EVENTS if e in ev_list]

def parse_events_str(s: str):
    if not s or not isinstance(s, str):
        return []
    parts = [p.strip() for p in s.split("|") if p.strip()]
    return [e for e in EVENTS if e in parts]

def highlight_text(text: str):
    esc = (
        (text or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
    out = esc
    for pat in HILITE_PATTERNS:
        out = re.sub(pat, lambda m: f"<mark>{m.group(0)}</mark>", out, flags=re.I)
    return out

def go_next():
    st.session_state.cursor = min(st.session_state.cursor + 1, len(item_ids) - 1)
    st.session_state.edit_note = ""

def go_prev():
    st.session_state.cursor = max(st.session_state.cursor - 1, 0)
    st.session_state.edit_note = ""
    
@st.cache_data(show_spinner=False)
def load_jsonl_cached(path: str):
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            if not isinstance(r, dict):
                continue
            r["_idx"] = i
            tnorm = normalize_text(r.get("text", ""))
            r["_id"] = r.get("id") or (sha1_hex(tnorm) if tnorm else f"row_{i}")
            rows.append(r)
    id2pos = {r["_id"]: k for k, r in enumerate(rows)}
    return rows, id2pos

@st.cache_data(show_spinner=False)
def load_queue_csv_cached(path: str):
    df = pd.read_csv(path)
    for c in [
        "idx", "id", "text", "intent", "urgency", "events",
        "reasons", "suggest_intent", "suggest_urgency", "suggest_events", "keyword_hits",
    ]:
        if c not in df.columns:
            df[c] = ""
    df["id"] = df["id"].astype(str)
    return df

def append_log(log_path: str, rec: dict):
    os.makedirs(os.path.dirname(log_path) or ".", exist_ok=True)
    file_exists = os.path.exists(log_path)
    cols = [
        "ts", "id", "idx",
        "old_intent", "new_intent",
        "old_urgency", "new_urgency",
        "old_events", "new_events",
        "reasons", "note",
    ]
    line = {k: rec.get(k, "") for k in cols}
    with open(log_path, "a", encoding="utf-8") as f:
        if not file_exists:
            f.write("\t".join(cols) + "\n")
        f.write("\t".join(str(line[k]) for k in cols) + "\n")

def write_jsonl(path: str, rows: list):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            rr = dict(r)
            rr.pop("_idx", None)
            rr.pop("_id", None)
            rr["events"] = stable_events(rr.get("events", []))
            f.write(json.dumps(rr, ensure_ascii=False) + "\n")

# =====================
# Streamlit UI
# =====================
st.set_page_config(page_title="MZone Dataset Review", layout="wide")
st.title("MZone Dataset Review — Mode: Batch Editor / Single Review")

with st.sidebar:
    st.header("Paths")
    data_path = st.text_input(
        "Dataset JSONL path",
        value=r"D:\MzoneDeploy\mzone-staging\dataset\splits_v5_audit\train.jsonl",
    )
    queue_path = st.text_input(
        "Queue CSV path (optional, dari audit_queue.py)",
        value=r"D:\MzoneDeploy\mzone-staging\dataset\splits_v5_audit\train_review_queue.csv",
    )
    out_fixed_path = st.text_input(
        "Output fixed JSONL",
        value=r"D:\MzoneDeploy\mzone-staging\dataset\splits_v5_audit\audit_train.jsonl",
    )
    log_path = st.text_input(
        "Change log TSV",
        value=r"D:\MzoneDeploy\mzone-staging\dataset\splits_v5_audit\changes_log.tsv",
    )

    st.divider()
    st.header("Audit Source Mode")
    mode = st.radio("Pilih source", ["Queue Review", "Search/Filter"], index=0)

    st.divider()
    st.header("Review UI Mode")
    review_ui = st.radio("Pilih tampilan", ["Batch Editor", "Single Review"], index=1)
    batch_size = st.slider("Batch size (Batch Editor)", 10, 100, 25, 5)

    st.divider()
    st.header("Queue filters (Queue Review)")
    reason_filter = st.text_input("Filter reasons contains (optional)", value="")
    show_only_with_suggestions = st.checkbox("Hanya yang ada suggestion", value=False)

    st.divider()
    st.header("Search/Filter (kalau mode Search/Filter)")
    f_keyword = st.text_input("Keyword/regex", value="")
    f_event = st.selectbox("Event", ["(any)"] + EVENTS, index=0)
    f_urg = st.selectbox("Urgency", ["(any)"] + URGENCY, index=0)
    f_int = st.selectbox("Intent", ["(any)"] + INTENT, index=0)

# =====================
# Load dataset into session_state
# =====================
if not data_path or not os.path.exists(data_path):
    st.error("Dataset path tidak valid / file tidak ditemukan.")
    st.stop()

if st.session_state.get("dataset_path") != data_path:
    raw_rows, raw_id2pos = load_jsonl_cached(data_path)
    rows = [dict(r) for r in raw_rows]
    id2pos = dict(raw_id2pos)

    st.session_state.dataset_path = data_path
    st.session_state.rows = rows
    st.session_state.id2pos = id2pos
    st.session_state.history = []
    st.session_state.cursor = 0
    st.session_state.page = 0
    st.session_state._cur_loaded_id = None

rows = st.session_state.rows
id2pos = st.session_state.id2pos

# =====================
# Build item list (queue / search)
# =====================
queue_df = None
item_ids = []

def get_queue_row(cur_id: str):
    if queue_df is None:
        return None
    q = queue_df[queue_df["id"].astype(str) == str(cur_id)]
    if len(q) == 0:
        return None
    return q.iloc[0].to_dict()

if mode == "Queue Review":
    if queue_path and os.path.exists(queue_path):
        base_df = load_queue_csv_cached(queue_path)
        df = base_df.copy()
        if reason_filter.strip():
            df = df[df["reasons"].astype(str).str.contains(reason_filter.strip(), case=False, na=False)]
        if show_only_with_suggestions:
            df = df[
                (df["suggest_intent"].astype(str).str.len() > 0)
                | (df["suggest_urgency"].astype(str).str.len() > 0)
                | (df["suggest_events"].astype(str).str.len() > 0)
            ]
        item_ids = [str(x) for x in df["id"].tolist() if str(x) in id2pos]
        queue_df = df.reset_index(drop=True)
    else:
        st.warning("Queue CSV tidak ditemukan. Jalankan audit_queue.py dulu atau gunakan mode Search/Filter.")
        mode = "Search/Filter"

if mode == "Search/Filter":
    kw = f_keyword.strip()
    pat = None
    if kw:
        try:
            pat = re.compile(kw, flags=re.I)
        except Exception:
            pat = None

    for r in rows:
        ok = True
        if f_event != "(any)":
            ok = ok and (f_event in safe_list(r.get("events", [])))
        if f_urg != "(any)":
            ok = ok and (r.get("urgency") == f_urg)
        if f_int != "(any)":
            ok = ok and (r.get("intent") == f_int)
        if pat is not None:
            ok = ok and bool(pat.search(r.get("text", "")))
        if ok:
            item_ids.append(r["_id"])

if not item_ids:
    st.info("Tidak ada item untuk direview (cek mode/filters).")
    st.stop()

# =====================
# Shared actions
# =====================
def stable_row_events(row_dict):
    return stable_events(row_dict.get("events", []))

def save_change(cur_id: str, new_intent: str, new_urg: str, new_events: list, note: str = "", reasons: str = ""):
    pos = id2pos[cur_id]
    r = rows[pos]

    old_intent = r.get("intent", "")
    old_urg = r.get("urgency", "")
    old_ev = stable_row_events(r)

    new_ev = stable_events(new_events)
    changed = (old_intent != new_intent) or (old_urg != new_urg) or (old_ev != new_ev)
    if not changed:
        return False

    st.session_state.history.append({
        "id": cur_id,
        "pos": pos,
        "old_intent": old_intent,
        "old_urgency": old_urg,
        "old_events": old_ev,
    })

    r["intent"] = new_intent
    r["urgency"] = new_urg
    r["events"] = new_ev

    append_log(log_path, {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "id": cur_id,
        "idx": r.get("_idx"),
        "old_intent": old_intent, "new_intent": new_intent,
        "old_urgency": old_urg, "new_urgency": new_urg,
        "old_events": "|".join(old_ev),
        "new_events": "|".join(new_ev),
        "reasons": reasons or "",
        "note": note or "",
    })
    return True

def undo_last():
    if not st.session_state.history:
        return False
    last = st.session_state.history.pop()
    pos = last["pos"]
    rows[pos]["intent"] = last["old_intent"]
    rows[pos]["urgency"] = last["old_urgency"]
    rows[pos]["events"] = last["old_events"]
    return True

# =====================
# UI: Batch Editor (TIDAK DIUBAH CSS-NYA)
# =====================
if review_ui == "Batch Editor":
    total = len(item_ids)
    pages = (total + batch_size - 1) // batch_size
    st.session_state.page = max(0, min(st.session_state.page, pages - 1))

    start = st.session_state.page * batch_size
    end = min(start + batch_size, total)
    batch_ids = item_ids[start:end]

    st.subheader(f"Batch Editor ({start+1}-{end} dari {total})")

    data = []
    for cid in batch_ids:
        r = rows[id2pos[cid]]
        ev = set(stable_row_events(r))
        row = {
            "id": cid,
            "idx": int(r.get("_idx", -1)),
            "text": (r.get("text", "") or "")[:180],
            "intent": r.get("intent", ""),
            "urgency": r.get("urgency", ""),
        }
        for e in EVENTS:
            row[f"EV_{e}"] = (e in ev)
        data.append(row)

    batch_df = pd.DataFrame(data)
    page_df_key = f"batch_df_page_{st.session_state.page}"
    if page_df_key not in st.session_state:
        st.session_state[page_df_key] = batch_df

    col_cfg = {
        "intent": st.column_config.SelectboxColumn("intent", options=INTENT, required=False),
        "urgency": st.column_config.SelectboxColumn("urgency", options=URGENCY, required=False),
        "text": st.column_config.TextColumn("text", width="large"),
    }
    for e in EVENTS:
        col_cfg[f"EV_{e}"] = st.column_config.CheckboxColumn(e, width="small")

    edited = st.data_editor(
        st.session_state[page_df_key],
        key=f"editor_{st.session_state.page}",
        use_container_width=True,
        hide_index=True,
        column_config=col_cfg,
        disabled=["id", "idx"],
    )

    c1, c2, c3, c4 = st.columns([1, 1, 1, 2])

    if c1.button("⬅ Prev page", disabled=(st.session_state.page == 0)):
        st.session_state.page -= 1
        st.rerun()

    if c2.button("Next page ➡", disabled=(st.session_state.page >= pages - 1)):
        st.session_state.page += 1
        st.rerun()

    if c3.button("💾 Save batch"):
        ed = edited.copy()
        saved = 0
        for i in range(len(ed)):
            cid = str(ed.loc[i, "id"])
            new_intent = str(ed.loc[i, "intent"]).strip()
            new_urg = str(ed.loc[i, "urgency"]).strip()
            if new_intent not in INTENT or new_urg not in URGENCY:
                continue
            new_ev = [e for e in EVENTS if bool(ed.loc[i, f"EV_{e}"])]
            if save_change(cid, new_intent, new_urg, new_ev, note="batch_save", reasons=""):
                saved += 1
        st.success(f"Saved batch changes: {saved} row(s). Log: {log_path}")
        st.session_state[page_df_key] = ed

    if c4.button("📦 Export fixed JSONL"):
        write_jsonl(out_fixed_path, rows)
        st.success(f"Export done ✓ → {out_fixed_path}")
        st.info(f"Log: {log_path}")

    st.stop()

# =====================
# UI: Single Review (Right sidebar fixed + center text NOT overlap)
# =====================
st.subheader("Single Review (center text fixed + right sidebar)")

RIGHT_W = 420
RIGHT_GAP = 26
TOP_OFFSET = 96  # kalau masih nabrak header, naikin jadi 110/120

st.markdown(
    f"""
    <style>
    /* Aktif hanya jika anchor ada */
    div[data-testid="stAppViewContainer"]:has(#mzone-right-anchor) div[data-testid="stMainBlockContainer"],
    div[data-testid="stAppViewContainer"]:has(#mzone-right-anchor) section.main > div.block-container,
    div[data-testid="stAppViewContainer"]:has(#mzone-right-anchor) .main .block-container {{
        padding-right: {RIGHT_W + RIGHT_GAP}px !important;
    }}

    /* Kotak text (scroll internal) */
    .mzone-textbox {{
        height: calc(100vh - 260px);
        overflow-y: auto;
        padding: 14px 16px;
        border: 1px solid rgba(49, 51, 63, 0.20);
        border-radius: 12px;
        background: rgba(255,255,255,0.02);
        white-space: pre-wrap;
        line-height: 1.5;
        font-size: 1.05rem;
        box-sizing: border-box;
        width: 100%;
    }}

    /* Sidebar kanan: column yang mengandung anchor */
    div[data-testid="stColumn"]:has(#mzone-right-anchor) {{
        position: fixed !important;
        top: {TOP_OFFSET}px;
        right: 14px;
        width: {RIGHT_W}px !important;
        height: calc(100vh - {TOP_OFFSET + 18}px);
        overflow-y: auto;
        padding: 12px 12px;
        border: 1px solid rgba(49, 51, 63, 0.20);
        border-radius: 12px;
        background: rgba(255,255,255,0.02);
        z-index: 9999;
    }}

    /* tombol full width */
    div[data-testid="stColumn"]:has(#mzone-right-anchor) button {{
        width: 100%;
    }}

    /* layar kecil fallback (biar tetap kebaca) */
    @media (max-width: 1200px) {{
        div[data-testid="stAppViewContainer"]:has(#mzone-right-anchor) div[data-testid="stMainBlockContainer"],
        div[data-testid="stAppViewContainer"]:has(#mzone-right-anchor) section.main > div.block-container,
        div[data-testid="stAppViewContainer"]:has(#mzone-right-anchor) .main .block-container {{
            padding-right: 1rem !important;
        }}
        div[data-testid="stColumn"]:has(#mzone-right-anchor) {{
            position: static !important;
            width: 100% !important;
            height: auto !important;
            overflow: visible !important;
            flex: 1 1 100% !important;
        }}
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

# clamp cursor
st.session_state.cursor = max(0, min(st.session_state.cursor, len(item_ids) - 1))
cur_id = item_ids[st.session_state.cursor]
cur = rows[id2pos[cur_id]]
qrow = get_queue_row(cur_id)  # reasons tidak ditampilkan

# init edit state when moving to new item
if st.session_state.get("_cur_loaded_id") != cur_id:
    st.session_state._cur_loaded_id = cur_id
    st.session_state.edit_intent = cur.get("intent", INTENT[0]) if cur.get("intent") in INTENT else INTENT[0]
    st.session_state.edit_urgency = cur.get("urgency", URGENCY[1]) if cur.get("urgency") in URGENCY else URGENCY[1]
    st.session_state.edit_events = stable_row_events(cur)
    st.session_state.edit_note = ""

def go_next():
    st.session_state.cursor = min(st.session_state.cursor + 1, len(item_ids) - 1)

def go_prev():
    st.session_state.cursor = max(st.session_state.cursor - 1, 0)

def set_intent(x): 
    st.session_state.edit_intent = x

def set_urg(x): 
    st.session_state.edit_urgency = x

def toggle_event(ev: str):
    s = set(st.session_state.edit_events)
    if ev in s:
        s.remove(ev)
    else:
        s.add(ev)
    st.session_state.edit_events = stable_events(list(s))

def mark(active: bool, label: str) -> str:
    return f"✅ {label}" if active else f"⬜ {label}"

def apply_suggestion_to_state(qrow_dict, replace_events=False):
    if not qrow_dict:
        return
    sug_i = str(qrow_dict.get("suggest_intent", "") or "").strip()
    sug_u = str(qrow_dict.get("suggest_urgency", "") or "").strip()
    sug_e = parse_events_str(str(qrow_dict.get("suggest_events", "") or ""))

    if sug_i in INTENT:
        st.session_state.edit_intent = sug_i
    if sug_u in URGENCY:
        st.session_state.edit_urgency = sug_u

    if sug_e:
        if replace_events:
            st.session_state.edit_events = stable_events(sug_e)
        else:
            curset = set(st.session_state.edit_events)
            curset |= set(sug_e)
            st.session_state.edit_events = stable_events(list(curset))

# Header / progress
topA, topB, topC, topD = st.columns([1, 2, 3, 2])
with topA:
    st.metric("Progress", f"{st.session_state.cursor+1}/{len(item_ids)}")
with topB:
    st.write(f"**id:** `{cur_id}`")
    st.write(f"**idx:** `{cur.get('_idx')}`")
with topC:
    st.write("**Current labels**")
    st.write(f"- intent: `{cur.get('intent')}`")
    st.write(f"- urgency: `{cur.get('urgency')}`")
    st.write(f"- events: `{', '.join(stable_row_events(cur))}`")
with topD:
    j = st.number_input("Jump to (1-based)", 1, len(item_ids), st.session_state.cursor + 1, 1)
    if int(j) != (st.session_state.cursor + 1):
        st.session_state.cursor = int(j) - 1
        st.rerun()

# Layout: kiri text, kanan dummy tipis (panel kanan jadi fixed)
left, right = st.columns([1, 0.001], gap="small")

with left:
    st.markdown("### Text (review)")
    st.markdown(
        f"<div class='mzone-textbox'>{highlight_text(cur.get('text',''))}</div>",
        unsafe_allow_html=True,
    )

with right:
    # WAJIB: anchor biar CSS :has(...) aktif
    st.markdown("<div id='mzone-right-anchor'></div>", unsafe_allow_html=True)

    st.markdown("### Panel (edit)")

    st.caption(f"**Intent:** {st.session_state.edit_intent}")
    st.caption(f"**Urgency:** {st.session_state.edit_urgency}")
    st.caption("**Events:** " + (", ".join(st.session_state.edit_events) if st.session_state.edit_events else "-"))
    st.divider()

    # Quick Intent
    with st.expander("Quick Intent", expanded=True):
        for val in INTENT:
            st.button(
                mark(st.session_state.edit_intent == val, val),
                key=f"qi_{val}",
                on_click=set_intent,
                args=(val,),
                use_container_width=True,
            )

    # Quick Urgency
    with st.expander("Quick Urgency", expanded=True):
        for val in URGENCY:
            st.button(
                mark(st.session_state.edit_urgency == val, val),
                key=f"qu_{val}",
                on_click=set_urg,
                args=(val,),
                use_container_width=True,
            )

    # Events toggle
    with st.expander("Events (toggle)", expanded=True):
        cL, cR = st.columns(2)
        cols = [cL, cR]
        for i, ev in enumerate(EVENTS):
            cols[i % 2].button(
                mark(ev in st.session_state.edit_events, ev),
                key=f"qe_{ev}",
                on_click=toggle_event,
                args=(ev,),
                use_container_width=True,
            )

        if st.button("🧹 Clear events", use_container_width=True, key="clr_events"):
            st.session_state.edit_events = []
            st.rerun()

    # Queue helper (optional)
    replace_events = st.checkbox("Replace events when applying suggestion", value=False)
    if st.button("✨ Apply Suggestions", disabled=(mode != "Queue Review" or not qrow), use_container_width=True):
        apply_suggestion_to_state(qrow, replace_events=replace_events)
        st.rerun()

    if st.button("↩ Undo", use_container_width=True):
        _ = undo_last()
        st.rerun()

    st.divider()

    # Note + Nav
    st.session_state.edit_note = st.text_input("Note (optional)", value=st.session_state.get("edit_note", ""))

    r1, r2 = st.columns(2)
    if r1.button("⬅ Prev", use_container_width=True):
        go_prev()
        st.rerun()
    if r2.button("✅ Next (Keep)", use_container_width=True):
        go_next()
        st.rerun()

    r3, r4 = st.columns(2)
    if r3.button("💾 Next (Save)", use_container_width=True):
        reasons = (qrow.get("reasons", "") if qrow else "")
        _ = save_change(
            cur_id,
            st.session_state.edit_intent,
            st.session_state.edit_urgency,
            st.session_state.edit_events,
            note=st.session_state.edit_note,
            reasons=reasons,
        )
        go_next()
        st.rerun()

    if r4.button("📦 Export fixed JSONL", use_container_width=True):
        write_jsonl(out_fixed_path, rows)
        st.success(f"Export done ✓ → {out_fixed_path}")
        st.info(f"Log: {log_path}")
        st.stop()
