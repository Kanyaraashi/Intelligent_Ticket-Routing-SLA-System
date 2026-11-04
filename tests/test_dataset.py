import json, re
from pathlib import Path
from src import metrics, build
from src.anomalies import detect_anomalies, evaluate_detection
from src.validation import validate

def test_row_counts(conn):
    n = lambda t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
    assert (n("ticket"), n("agent"), n("message")) == (500, 20, 2000)
def test_deterministic_ids(conn):
    assert conn.execute("SELECT MIN(ticket_id),MAX(ticket_id) FROM ticket").fetchone() == ("TKT-2026-000001", "TKT-2026-000500")
    assert conn.execute("SELECT message_id FROM message WHERE ticket_id='TKT-2026-000001' AND seq=1").fetchone()[0] == "MSG-TKT-2026-000001-001"
    assert conn.execute("SELECT sla_event_id FROM sla_event WHERE ticket_id='TKT-2026-000001' AND seq=1").fetchone()[0] == "SLA-TKT-2026-000001"
    assert re.match(r"ASN-TKT-2026-000001-001", conn.execute("SELECT assignment_id FROM assignment_event WHERE ticket_id='TKT-2026-000001' AND seq=1").fetchone()[0])
def test_foreign_keys(conn): assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
def test_thirteen_core_entities(conn):
    names = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"customer","channel","ticket","message","intent","language","priority_rule","agent","skill","queue","assignment_event","sla_event","resolution"} <= names
def test_routing_hard_constraints_never_violated(conn):
    k = metrics.kpis(conn); assert k["skill_mismatches"] == 0 and k["language_mismatches"] == 0
def test_shift_respected_on_assignment(conn):
    assert not [i for i in validate(conn) if i["check"] == "SKILLS_AND_LANGUAGES"]
def test_five_anomalies_detected(conn, starter):
    gt = json.loads((starter["gt"]/"ground_truth.json").read_text()); assert len(gt) == 5
    res, _ = evaluate_detection(detect_anomalies(conn), gt); assert all(r["detected"] for r in res)
    assert {g["issue_type"] for g in gt} == {"CAPACITY_EXCEEDED","SLA_IGNORES_CALENDAR","REOPEN_HISTORY_LOST","TRANSFER_LOOP","SAFETY_PRIORITY_VIOLATION"}
def test_ground_truth_files_have_required_fields(starter):
    g = json.loads((starter["gt"]/"ground_truth.json").read_text())[0]
    assert {"anomaly_id","related_record_id","issue_type","description","severity","expected_detection","expected_decision"} <= set(g)
    assert (starter["gt"]/"ground_truth.csv").exists()
def test_no_accidental_integrity_failures(conn, starter):
    gt = json.loads((starter["gt"]/"ground_truth.json").read_text()); ids = {g["related_record_id"] for g in gt}
    assert [i for i in validate(conn) if i["record_id"] not in ids] == []
def test_ground_truth_not_imported_by_application_code():
    src = "".join(p.read_text() for p in Path("src").glob("*.py") if p.name not in ("anomalies.py", "build.py"))
    assert "ground_truth" not in src
def test_lifecycle_history_valid(conn): assert not [i for i in validate(conn) if i["check"] == "LIFECYCLE_TRANSITIONS"]
def test_reopen_keeps_history(conn):
    rows = conn.execute("SELECT ticket_id,reopen_count FROM ticket WHERE reopen_count>0").fetchall(); assert rows
    ok = 0
    for tid, rc in rows:
        if conn.execute("SELECT COUNT(*) FROM resolution WHERE ticket_id=?", (tid,)).fetchone()[0] >= rc: ok += 1
    assert ok >= len(rows) - 1                                    # one ticket has the injected anomaly
def test_metrics_derived_from_db(conn):
    k = metrics.kpis(conn)
    assert k["total_tickets"] == conn.execute("SELECT COUNT(*) FROM ticket").fetchone()[0] == 500
    assert k["resolved_tickets"] + k["open_tickets"] == 500 and 0 <= k["sla_compliance_pct"] <= 100
def test_escalation_recorded(conn):
    assert conn.execute("SELECT COUNT(*) FROM assignment_event WHERE event_type='ESCALATE'").fetchone()[0] > 0
def test_unassigned_reason_recorded(conn):
    assert conn.execute("SELECT COUNT(*) FROM assignment_event WHERE event_type='UNASSIGNED' AND reason_code!=''").fetchone()[0] > 0
def test_reproducible(tmp_path, starter):
    m2 = build.generate("starter", db_path=tmp_path/"b.db", export_dir=tmp_path/"e", gt_dir=tmp_path/"g", quiet=True); m1 = starter["manifest"]
    assert m1["record_counts"] == m2["record_counts"] and m1["table_checksums"] == m2["table_checksums"] and m1["export_checksums"] == m2["export_checksums"]
