"""Creates docs/VALIDATION_REPORT.md from the real databases (KPIs, validation, anomaly detection)."""
import _boot, json
from datetime import datetime, timezone
from src import db, metrics
from src.validation import validate, summarize
from src.anomalies import detect_anomalies, evaluate_detection
out = ["# Validation & KPI Report", f"_Generated {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC from the actual SQLite databases._", ""]
for mode in ("starter", "full"):
    p = db.ROOT/"data"/f"{mode}.db"
    if not p.exists(): out += [f"## {mode}: database not generated", ""]; continue
    c = db.connect(p, readonly=True); k = metrics.kpis(c); iss = validate(c); gtp = db.ROOT/"data"/f"ground_truth_{mode}"/"ground_truth.json"
    out += [f"## Dataset: {mode}", "", "### KPIs", "| KPI | Value |", "|---|---|"] + [f"| {a} | {round(b, 2) if isinstance(b, float) else b} |" for a, b in k.items()]
    out += ["", "### Validation checks", "| Check | Issues | Status |", "|---|---|---|"] + [f"| {r.check} | {r.issues} | {r.status} |" for r in summarize(iss).itertuples()]
    if gtp.exists():
        gt = json.loads(gtp.read_text()); res, _ = evaluate_detection(detect_anomalies(c), gt); ids = {g["related_record_id"] for g in gt}
        acc = [i for i in iss if i["record_id"] not in ids]
        out += ["", "### Injected anomalies (detector vs ground truth)", "| Anomaly | Type | Record | Detected |", "|---|---|---|---|"] + [f"| {r['anomaly_id']} | {r['issue_type']} | {r['related_record_id']} | {'YES' if r['detected'] else 'NO'} |" for r in res]
        out += ["", f"Validation issues total: {len(iss)}; attributable to injected anomalies (incl. knock-on effects): {len(iss)-len(acc)}; **accidental integrity failures: {len(acc)}**", ""]
        out += [f"- ACCIDENTAL {i['check']} {i['record_id']}: {i['detail']}" for i in acc[:30]]
    c.close()
(db.ROOT/"docs"/"VALIDATION_REPORT.md").write_text("\n".join(out) + "\n", encoding="utf-8"); print("\n".join(out[:60])); print("\nWritten: docs/VALIDATION_REPORT.md")
