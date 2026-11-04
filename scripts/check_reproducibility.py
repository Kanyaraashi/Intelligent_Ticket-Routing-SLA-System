"""Runs the generator twice with identical config+seed and compares counts, IDs, table checksums and export checksums."""
import _boot, argparse, json, shutil, sqlite3
from src import build, db
ap = argparse.ArgumentParser(); ap.add_argument("--mode", default="starter"); a = ap.parse_args()
tmp = db.ROOT/"data"/f"_repro_{a.mode}"; shutil.rmtree(tmp, ignore_errors=True)
m = [build.generate(a.mode, db_path=tmp/f"run{i}.db", export_dir=tmp/f"exp{i}", gt_dir=tmp/f"gt{i}", quiet=True) for i in (1, 2)]
ids = []
for i in (1, 2):
    c = sqlite3.connect(tmp/f"run{i}.db"); ids.append([c.execute(f"SELECT {k} FROM {t} ORDER BY 1").fetchall() for t, k in [("ticket","ticket_id"),("message","message_id"),("agent","agent_id"),("assignment_event","assignment_id"),("sla_event","sla_event_id")]]); c.close()
gt_same = (tmp/"gt1"/"ground_truth.json").read_bytes() == (tmp/"gt2"/"ground_truth.json").read_bytes()
res = dict(mode=a.mode, seed=m[0]["seed"], row_counts_identical=m[0]["record_counts"] == m[1]["record_counts"], ids_identical=ids[0] == ids[1],
           table_checksums_identical=m[0]["table_checksums"] == m[1]["table_checksums"], export_checksums_identical=m[0]["export_checksums"] == m[1]["export_checksums"],
           ground_truth_identical=gt_same, record_counts=m[0]["record_counts"], tables_compared=len(m[0]["table_checksums"]), export_files_compared=len(m[0]["export_checksums"]),
           excluded_from_determinism_checks=m[0]["excluded_from_determinism_checks"])
res["REPRODUCIBLE"] = all(res[k] for k in ["row_counts_identical", "ids_identical", "table_checksums_identical", "export_checksums_identical", "ground_truth_identical"])
(db.ROOT/"data"/f"reproducibility_report_{a.mode}.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
print(json.dumps({k: v for k, v in res.items() if k != "record_counts"}, indent=2)); shutil.rmtree(tmp, ignore_errors=True)
raise SystemExit(0 if res["REPRODUCIBLE"] else 1)
