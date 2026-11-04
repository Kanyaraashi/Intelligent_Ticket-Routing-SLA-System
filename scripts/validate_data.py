import _boot, argparse, json
from pathlib import Path
from src import db
from src.validation import validate, summarize
from src.anomalies import detect_anomalies, evaluate_detection
ap = argparse.ArgumentParser(); ap.add_argument("--mode", default="starter"); a = ap.parse_args()
conn = db.connect(db.ROOT/"data"/f"{a.mode}.db", readonly=True)
issues = validate(conn); print(summarize(issues).to_string(index=False))
gtp = db.ROOT/"data"/f"ground_truth_{a.mode}"/"ground_truth.json"
if gtp.exists():
    gt = json.loads(gtp.read_text()); res, extra = evaluate_detection(detect_anomalies(conn), gt)
    print("\nInjected-anomaly detection (evaluation vs ground truth):"); [print("  ", r) for r in res]
    keys = {(g["related_record_id"]) for g in gt}
    acc = [i for i in issues if i["record_id"] not in keys]
    print(f"\nTotal validation issues: {len(issues)}; matching injected anomalies: {len(issues)-len(acc)}; ACCIDENTAL (not in ground truth): {len(acc)}")
    [print("   ACCIDENTAL:", i) for i in acc[:20]]
