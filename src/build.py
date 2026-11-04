"""Orchestrates: generate -> persist -> inject anomalies -> exports -> manifest."""
import csv, hashlib, json, os, random, sqlite3, time
from datetime import datetime, timezone
from pathlib import Path
from . import db, generator as g
from .anomalies import inject_anomalies

TABLES = ["language","channel","skill","queue","intent","intent_skill","priority_rule","sla_policy","holiday","agent","agent_skill","agent_language","agent_shift",
          "customer","ticket","ticket_status_history","message","assignment_event","sla_event","resolution"]

def load_modes():
    return json.loads((db.ROOT/"config"/"modes.json").read_text(encoding="utf-8"))

def table_checksum(conn, t):
    h = hashlib.sha256()
    for row in conn.execute(f"SELECT * FROM {t} ORDER BY 1,2"): h.update(repr(row).encode())
    return h.hexdigest()

def file_sha(p):
    h = hashlib.sha256(); h.update(Path(p).read_bytes()); return h.hexdigest()

def export_all(conn, out):
    out.mkdir(parents=True, exist_ok=True); names = []
    for t in TABLES:
        cur = conn.execute(f"SELECT * FROM {t}"); cols = [c[0] for c in cur.description]; rows = cur.fetchall()
        with open(out/f"{t}.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f, lineterminator="\n"); w.writerow(cols); w.writerows(rows)
        (out/f"{t}.json").write_text(json.dumps([dict(zip(cols, r)) for r in rows], separators=(",", ":")), encoding="utf-8")
        names += [f"{t}.csv", f"{t}.json"]
    return names

def generate(mode, db_path=None, export_dir=None, seed=None, inject=True, gt_dir=None, quiet=False):
    modes = load_modes(); cfg = dict(modes["modes"][mode]); cfg["start_date"] = modes["start_date"]; seed = seed or modes["seed"]
    root = db.ROOT; db_path = Path(db_path or root/"data"/f"{mode}.db"); export_dir = Path(export_dir or root/"exports"/mode); gt_dir = Path(gt_dir or root/"data"/f"ground_truth_{mode}")
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists(): db_path.unlink()
    t0 = time.time(); rng = random.Random(seed)
    conn, rules, agents, custs, T, rows, end = g.generate_data(cfg, seed, db_path)
    msgs = g.build_messages(rng, cfg, T, end)
    g.persist(conn, cfg, seed, mode, rules, agents, custs, T, rows, msgs, end)
    gt = inject_anomalies(conn, gt_dir) if inject else []
    names = export_all(conn, export_dir)
    counts = {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in TABLES}
    manifest = dict(generator_version=modes["generator_version"], seed=seed, mode=mode, configuration=cfg, anomalies_injected=len(gt),
                    generation_timestamp_utc=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), record_counts=counts, export_names=names,
                    table_checksums={t: table_checksum(conn, t) for t in TABLES}, export_checksums={n: file_sha(export_dir/n) for n in names},
                    excluded_from_determinism_checks=["generation_timestamp_utc", "SQLite file bytes (page layout)", "runtime seconds"])
    (export_dir/"source_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    conn.close()
    if not quiet: print(f"[{mode}] done in {time.time()-t0:.1f}s -> {db_path}")
    return manifest
