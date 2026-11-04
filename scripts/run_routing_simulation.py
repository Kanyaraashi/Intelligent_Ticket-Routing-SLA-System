"""Demonstrates read-only routing simulation on the starter DB and proves the DB is unchanged."""
import _boot, hashlib
from datetime import datetime
from src import db, simulation
path = db.ROOT/"data"/"starter.db"; before = hashlib.sha256(path.read_bytes()).hexdigest()
conn = db.connect(path, readonly=True)
cases = [("EMAIL","en","STANDARD","Charger overheating","My charger is overheating and there was smoke.", datetime(2026,7,8,10,0)),
         ("CHAT","hi","GOLD","Cannot log in","I cannot log in and I am locked out.", datetime(2026,7,8,10,0)),
         ("EMAIL","en","STANDARD","Where is my order 123","Where is my order? Tracking has not updated.", datetime(2026,7,4,23,30)),
         ("PHONE","pt","PLATINUM","Refund request","I want a refund, my money back asap.", datetime(2026,7,8,3,0))]
for c in cases:
    r = simulation.simulate(conn, *c); d = r["decision"]
    print(f"{c[0]:5s} lang={c[1]} -> intent={r['intent']} prio={r['priority']} queue={r['queue']} due={r['response_due']} | agent={d.agent_id} score={d.score} reason={d.reason_code} | eligible={len(d.candidates)} rejected={len(d.rejected)}")
conn.close(); after = hashlib.sha256(path.read_bytes()).hexdigest()
print("Database unchanged by simulation:", before == after)
