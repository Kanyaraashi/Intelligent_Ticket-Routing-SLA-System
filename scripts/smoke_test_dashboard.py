"""Runs every dashboard page headlessly with Streamlit's AppTest and fails on any exception."""
import _boot, sys
from streamlit.testing.v1 import AppTest
from src import db
ok = True
for mode in [m for m in ("starter", "full") if (db.ROOT/"data"/f"{m}.db").exists()]:
    for page in ["Executive Overview","Ticket Explorer","Intelligent Routing","Agent Performance","SLA Monitoring","Queue Analytics","Anomaly Detection","Data Validation","About the Project"]:
        at = AppTest.from_file(str(db.ROOT/"app.py"), default_timeout=180); at.run()
        at.sidebar.selectbox[0].set_value(mode); at.sidebar.radio[0].set_value(page); at.run()
        if page == "Intelligent Routing": at.button[0].click(); at.run()
        status = "OK " if not at.exception else "ERR"; ok &= not at.exception
        print(f"[{status}] {mode:8s} {page}" + (f"  -> {at.exception[0].value}" if at.exception else ""))
sys.exit(0 if ok else 1)
