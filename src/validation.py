"""Data validation. Returns issues as dicts(check, severity, record_id, detail). Never reads ground truth."""
import json, re
from datetime import timedelta
from config.reference_data import TRANSITIONS, PRIORITIES
from .anomalies import detect_anomalies
from .rules import RuleSet
from .routing import shift_remaining
from .timeutil import parse
import pandas as pd

ID_PATTERNS = {"ticket": ("ticket_id", r"^TKT-2026-\d{6}$"), "message": ("message_id", r"^MSG-TKT-2026-\d{6}-\d{3}$"), "agent": ("agent_id", r"^AGT-\d{6}$"),
               "assignment_event": ("assignment_id", r"^ASN-TKT-2026-\d{6}-\d{3}$"), "sla_event": ("sla_event_id", r"^SLA-TKT-2026-\d{6}(-\d{2})?$")}
CHECKS = ["PRIMARY_KEY_UNIQUENESS", "FOREIGN_KEY_INTEGRITY", "ALLOWED_VALUES", "REQUIRED_FIELDS", "DUPLICATE_RECORDS", "DATE_ORDERING", "LIFECYCLE_TRANSITIONS",
          "ASSIGNMENT_HISTORY", "AGENT_CAPACITY", "SKILLS_AND_LANGUAGES", "SLA_CALCULATIONS", "ESCALATION_TIMING", "MESSAGE_THREADS", "REOPEN_HISTORY", "DERIVED_VALUES", "TRANSFER_LOOPS", "PRIORITY_RULES"]

def validate(conn):
    I = []; add = lambda c, s, r, d: I.append(dict(check=c, severity=s, record_id=r, detail=d))
    q = lambda sql, *a: conn.execute(sql, a).fetchall()
    # 1 PK / id format
    for tbl, (col, rx) in ID_PATTERNS.items():
        for (v,) in q(f"SELECT {col} FROM {tbl}"):
            if not re.match(rx, v): add("PRIMARY_KEY_UNIQUENESS", "HIGH", v, f"{tbl}.{col} violates ID convention")
        for (v, n) in q(f"SELECT {col},COUNT(*) FROM {tbl} GROUP BY 1 HAVING COUNT(*)>1"): add("PRIMARY_KEY_UNIQUENESS", "HIGH", v, f"duplicate key in {tbl}")
    # 2 FK
    for tbl, rid, parent, fk in conn.execute("PRAGMA foreign_key_check").fetchall(): add("FOREIGN_KEY_INTEGRITY", "HIGH", str(rid), f"{tbl} -> {parent} ({fk})")
    # 3 allowed values (CHECK constraints already enforce; re-verify semantically)
    for (v,) in q("SELECT ticket_id FROM ticket WHERE priority NOT IN ('LOW','MEDIUM','HIGH','CRITICAL') OR status NOT IN ('NEW','OPEN','ASSIGNED','IN_PROGRESS','PENDING_CUSTOMER','RESOLVED','CLOSED','REOPENED','ESCALATED')"): add("ALLOWED_VALUES", "HIGH", v, "invalid enum")
    # 4 required fields (conditional)
    for (v,) in q("SELECT ticket_id FROM ticket WHERE status IN ('ASSIGNED','IN_PROGRESS','PENDING_CUSTOMER') AND current_agent_id IS NULL"): add("REQUIRED_FIELDS", "HIGH", v, "active ticket without current agent")
    for (v,) in q("SELECT ticket_id FROM ticket WHERE status IN ('RESOLVED','CLOSED') AND resolved_at_utc IS NULL"): add("REQUIRED_FIELDS", "HIGH", v, "resolved/closed ticket without resolved_at")
    for (v,) in q("SELECT ticket_id FROM ticket WHERE status='CLOSED' AND closed_at_utc IS NULL"): add("REQUIRED_FIELDS", "HIGH", v, "closed ticket without closed_at")
    # 5 duplicates
    for (c, s, at, n) in q("SELECT customer_id,subject,created_at_utc,COUNT(*) FROM ticket GROUP BY 1,2,3 HAVING COUNT(*)>1"): add("DUPLICATE_RECORDS", "MEDIUM", c, f"{n} tickets with same customer/subject/time")
    # 6 date ordering
    for (v,) in q("SELECT ticket_id FROM ticket WHERE first_response_at_utc<created_at_utc OR resolved_at_utc<first_response_at_utc OR closed_at_utc<resolved_at_utc"): add("DATE_ORDERING", "HIGH", v, "ticket timestamps out of order")
    for (v,) in q("SELECT assignment_id FROM assignment_event WHERE released_at_utc<event_at_utc"): add("DATE_ORDERING", "HIGH", v, "released before assigned")
    for (v,) in q("SELECT a.assignment_id FROM assignment_event a JOIN ticket t USING(ticket_id) WHERE a.event_at_utc<t.created_at_utc"): add("DATE_ORDERING", "HIGH", v, "assignment before ticket creation")
    # 7 lifecycle
    last = {}
    for tid, seq, fr, to in q("SELECT ticket_id,seq,from_status,to_status FROM ticket_status_history ORDER BY ticket_id,seq"):
        if seq == 1 and (fr is not None or to != "NEW"): add("LIFECYCLE_TRANSITIONS", "HIGH", tid, "must start with NEW")
        elif seq > 1 and to not in TRANSITIONS.get(fr, []): add("LIFECYCLE_TRANSITIONS", "HIGH", f"{tid}#{seq}", f"illegal {fr}->{to}")
        last[tid] = to
    for tid, st in q("SELECT ticket_id,status FROM ticket"):
        if last.get(tid) != st: add("LIFECYCLE_TRANSITIONS", "HIGH", tid, f"ticket.status {st} != last history {last.get(tid)}")
    # 8 assignment history
    for tid, n, mx in q("SELECT ticket_id,COUNT(*),MAX(seq) FROM assignment_event GROUP BY 1"):
        if n != mx: add("ASSIGNMENT_HISTORY", "HIGH", tid, "assignment sequence has gaps")
    for (v, n) in q("SELECT ticket_id,COUNT(*) FROM assignment_event WHERE to_agent_id IS NOT NULL AND released_at_utc IS NULL GROUP BY 1 HAVING COUNT(*)>1"): add("ASSIGNMENT_HISTORY", "HIGH", v, f"{n} simultaneous open assignments")
    for (v,) in q("""SELECT t.ticket_id FROM ticket t WHERE t.current_agent_id IS NOT NULL AND NOT EXISTS
                     (SELECT 1 FROM assignment_event a WHERE a.ticket_id=t.ticket_id AND a.to_agent_id=t.current_agent_id AND a.released_at_utc IS NULL)"""): add("ASSIGNMENT_HISTORY", "HIGH", v, "current agent has no open assignment")
    # 9 skills / languages / shift at assignment time
    rules = RuleSet.from_db(conn); sla = rules.sla
    ask = {}; [ask.setdefault(a, set()).add(s) for a, s in q("SELECT agent_id,skill_id FROM agent_skill")]
    alg = {}; [alg.setdefault(a, set()).add(l) for a, l in q("SELECT agent_id,language_code FROM agent_language")]
    shifts = {}; [shifts.setdefault(a, {}).setdefault(d, []).append((s, e)) for a, d, s, e in q("SELECT agent_id,weekday,start_min_utc,end_min_utc FROM agent_shift")]
    msg1 = {t: b for t, b in q("SELECT ticket_id,body FROM message WHERE seq=1")}
    tk = {r[0]: r for r in q("SELECT ticket_id,intent_id,language_code,subject,safety_flag FROM ticket")}
    for aid, tid, to, at in q("SELECT assignment_id,ticket_id,to_agent_id,event_at_utc FROM assignment_event WHERE to_agent_id IS NOT NULL"):
        _, intent, lang, subj, flag = tk[tid]
        safe = any(k in (subj + " " + msg1.get(tid, "")).lower() for k in rules.safety_keywords) or rules.intents[intent]["safety"]
        need = set(rules.required_skills(intent, safe))
        if not need <= ask.get(to, set()): add("SKILLS_AND_LANGUAGES", "HIGH", aid, f"agent {to} lacks skills {sorted(need - ask.get(to, set()))}")
        if lang not in alg.get(to, set()): add("SKILLS_AND_LANGUAGES", "HIGH", aid, f"agent {to} does not speak {lang}")
        if shift_remaining(shifts.get(to, {}), parse(at)) <= 0: add("SKILLS_AND_LANGUAGES", "MEDIUM", aid, f"agent {to} assigned outside shift (shift check)")
    # 10 SLA + 8b capacity + loops + safety priority via rule-based detector
    for d in detect_anomalies(conn):
        chk = {"CAPACITY_EXCEEDED": "AGENT_CAPACITY", "SLA_IGNORES_CALENDAR": "SLA_CALCULATIONS", "SLA_DEADLINE_MISMATCH": "SLA_CALCULATIONS", "REOPEN_HISTORY_LOST": "REOPEN_HISTORY",
               "TRANSFER_LOOP": "TRANSFER_LOOPS", "SAFETY_PRIORITY_VIOLATION": "PRIORITY_RULES"}[d["issue_type"]]
        add(chk, d["severity"], d["related_record_id"], f"{d['issue_type']}: {d['description']}")
    # SLA event consistency: response MET/BREACH vs timestamps
    for tid, typ, due, fr in q("""SELECT s.ticket_id,s.event_type,t.sla_response_due_utc,t.first_response_at_utc FROM sla_event s JOIN ticket t USING(ticket_id)
                                   WHERE s.target_type='RESPONSE' AND s.event_type IN ('MET','BREACH')"""):
        if typ == "MET" and fr and fr > due: add("SLA_CALCULATIONS", "MEDIUM", tid, "response marked MET but first response after due")
    # 11 escalation timing (first-cycle wait escalations)
    for tid, ch, pr, cr, at in q("""SELECT t.ticket_id,t.channel_id,t.priority,t.created_at_utc,a.event_at_utc FROM assignment_event a JOIN ticket t USING(ticket_id)
                                    WHERE a.event_type='ESCALATE' AND a.reason_code='WAIT_THRESHOLD_EXCEEDED' AND a.seq=(SELECT MIN(seq) FROM assignment_event x WHERE x.ticket_id=a.ticket_id AND x.event_type='ESCALATE')"""):
        due = sla.escalation_due(ch, pr, parse(cr) + timedelta(seconds=2))
        first_asg = conn.execute("SELECT MIN(event_at_utc) FROM assignment_event WHERE ticket_id=? AND to_agent_id IS NOT NULL", (tid,)).fetchone()[0]
        if parse(at) < due - timedelta(minutes=1) and parse(cr).year and (first_asg is None or at < first_asg):
            add("ESCALATION_TIMING", "MEDIUM", tid, f"escalated at {at} before threshold {due}")
    # 12 message threads
    prev = {}
    for tid, seq, st, ts, ag in q("SELECT ticket_id,seq,sender_type,sent_at_utc,sender_agent_id FROM message ORDER BY ticket_id,seq"):
        p = prev.get(tid)
        if p is None and (seq != 1 or st != "CUSTOMER"): add("MESSAGE_THREADS", "HIGH", tid, "thread must start with customer message seq 1")
        if p and (seq != p[0] + 1 or ts < p[1]): add("MESSAGE_THREADS", "HIGH", f"{tid}#{seq}", "sequence gap or time going backwards")
        prev[tid] = (seq, ts)
    for (v,) in q("SELECT t.ticket_id FROM ticket t JOIN message m ON m.ticket_id=t.ticket_id AND m.seq=1 WHERE m.sent_at_utc!=t.created_at_utc"): add("MESSAGE_THREADS", "MEDIUM", v, "first message not at ticket creation")
    for (v,) in q("""SELECT t.ticket_id FROM ticket t WHERE t.first_response_at_utc IS NOT NULL AND
                     (SELECT MIN(sent_at_utc) FROM message m WHERE m.ticket_id=t.ticket_id AND sender_type='AGENT')!=t.first_response_at_utc"""): add("DERIVED_VALUES", "MEDIUM", v, "first_response_at != earliest agent message")
    # 14 derived values
    for (v,) in q("SELECT t.ticket_id FROM ticket t WHERE t.transfer_count!=(SELECT COUNT(*) FROM assignment_event a WHERE a.ticket_id=t.ticket_id AND event_type='TRANSFER')"): add("DERIVED_VALUES", "MEDIUM", v, "transfer_count mismatch")
    for (v,) in q("SELECT t.ticket_id FROM ticket t WHERE t.reopen_count!=(SELECT COUNT(*) FROM ticket_status_history h WHERE h.ticket_id=t.ticket_id AND to_status='REOPENED')"): add("DERIVED_VALUES", "MEDIUM", v, "reopen_count mismatch")
    for (v,) in q("SELECT t.ticket_id FROM ticket t WHERE t.resolved_at_utc IS NOT (SELECT MAX(resolved_at_utc) FROM resolution r WHERE r.ticket_id=t.ticket_id)"): add("DERIVED_VALUES", "MEDIUM", v, "resolved_at != latest resolution")
    return I

def summarize(issues):
    df = pd.DataFrame(issues, columns=["check", "severity", "record_id", "detail"])
    rows = [dict(check=c, issues=int((df.check == c).sum()) if len(df) else 0) for c in CHECKS]
    for r in rows: r["status"] = "PASS" if r["issues"] == 0 else "ISSUES"
    return pd.DataFrame(rows)
