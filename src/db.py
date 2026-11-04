import json, sqlite3
from pathlib import Path
from config.reference_data import *
ROOT = Path(__file__).resolve().parent.parent
def connect(path, readonly=False):
    if readonly: conn = sqlite3.connect(f"file:{Path(path).resolve().as_posix()}?mode=ro", uri=True, check_same_thread=False)
    else: conn = sqlite3.connect(str(path))
    conn.execute("PRAGMA foreign_keys = ON"); return conn
def init_schema(conn): conn.executescript((ROOT/"database"/"schema.sql").read_text(encoding="utf-8"))
def seed_reference(conn, start_date="2026-01-01"):
    ef = "2026-01-01"
    conn.executemany("INSERT INTO language VALUES (?,?)", [(a, b) for a, b, _ in LANGUAGES])
    conn.executemany("INSERT INTO channel VALUES (?,?,?,?,?)", [c[:5] for c in CHANNELS])
    conn.executemany("INSERT INTO skill VALUES (?,?)", SKILLS)
    conn.executemany("INSERT INTO queue VALUES (?,?,?,1)", QUEUES)
    for iid, i in INTENTS.items():
        conn.execute("INSERT INTO intent VALUES (?,?,?,?,?,?)", (iid, i["name"], json.dumps(i["keywords"]), i["priority"], i["queue"], int(i.get("safety", False))))
        conn.executemany("INSERT INTO intent_skill VALUES (?,?)", [(iid, s) for s in i["skills"]])
    conn.executemany("INSERT INTO priority_rule VALUES (?,?,?,?,?,?,NULL)", [(a, b, c, d, e, ef) for a, b, c, d, e in PRIORITY_RULES])
    conn.executemany("INSERT INTO sla_policy VALUES (?,?,?,?,?,?,?,NULL)", [(*p, ef) for p in SLA_POLICY])
    conn.executemany("INSERT INTO holiday VALUES (?,?,?,?)", HOLIDAYS)
