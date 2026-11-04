"""Usage: python scripts/generate_data.py --mode starter|full"""
import _boot, argparse, json
from src.build import generate
ap = argparse.ArgumentParser(); ap.add_argument("--mode", choices=["starter", "full"], default="starter"); a = ap.parse_args()
m = generate(a.mode)
print("Row counts:"); [print(f"  {k:24s}{v:>8,}") for k, v in m["record_counts"].items()]
print("Exports written to exports/%s (CSV + JSON + source_manifest.json); ground truth in data/ground_truth_%s/" % (a.mode, a.mode))
