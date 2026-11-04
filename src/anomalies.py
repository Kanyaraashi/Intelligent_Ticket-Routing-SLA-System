"""Anomaly INJECTION (writes ground truth, separate files) and anomaly DETECTION (never reads ground truth)."""
import csv, json
from datetime import timedelta
from .timeutil import parse, fmt
from .rules import RuleSet
from .routing import shift_remaining

def _asof(conn): return parse(conn.execute("SELECT value FROM dataset_meta WHERE key='as_of_utc'").fetchone()[0])

def _agent_intervals(conn):
    as_of = _asof(conn); iv = {}
    for aid, to, at, rel in conn.execute("SELECT assignment_id,to_agent_id,event_at_utc,released_at_utc FROM assignment_event WHERE to_agent_id IS NOT NULL ORDER BY event_at_utc,assignment_id"):
        iv.setdefault(to, []).append((parse(at), parse(rel) if rel else as_of, aid))
    return iv

def capacity_violations(conn, caps=None):
    """-> {agent_id: (first_violating_assignment_id, n_violations, peak)}"""
    caps = caps or dict(conn.execute("SELECT agent_id,max_concurrent FROM agent"))
    out = {}
    for ag, ivs in _agent_intervals(conn).items():
        active, n, first, peak = [], 0, None, 0
        for s, e, aid in sorted(ivs):
            active = [x for x in active if x > s]; active.append(e)
            if len(active) > caps[ag]:
                n += 1; first = first or aid; peak = max(peak, len(active))
        if n: out[ag] = (first, n, peak)
    return out

def detect_anomalies(conn):
    """Return list of dicts(issue_type, related_record_id, description, severity). Pure rule-based; no ground-truth input."""
    rules = RuleSet.from_db(conn); sla = rules.sla; found = []
    for ag, (aid, n, peak) in capacity_violations(conn).items():
        found.append(dict(issue_type="CAPACITY_EXCEEDED", related_record_id=aid, severity="HIGH",
                          description=f"Agent {ag} exceeded max concurrency {n} time(s); peak {peak}."))
    pauses = {}
    for tid, typ, at in conn.execute("SELECT ticket_id,event_type,occurred_at_utc FROM sla_event WHERE event_type IN ('PAUSE','RESUME') ORDER BY ticket_id,seq"):
        pauses.setdefault(tid, []).append((typ, parse(at)))
    def pairs(tid):
        out, st = [], None
        for typ, at in pauses.get(tid, []):
            if typ == "PAUSE": st = at
            elif st: out.append((st, at)); st = None
        return out
    for tid, ch, pr, cr, rd, sd in conn.execute("SELECT ticket_id,channel_id,priority,created_at_utc,sla_response_due_utc,sla_resolution_due_utc FROM ticket"):
        c = parse(cr); er, es = sla.deadlines(ch, pr, c, pairs(tid)); r, s = parse(rd), parse(sd)
        if abs((r-er).total_seconds()) > 60 or abs((s-es).total_seconds()) > 60:
            tr, ts = sla.targets(ch, pr)
            wall = abs((r - (c+timedelta(minutes=tr))).total_seconds()) < 60 and abs((r-er).total_seconds()) > 60
            found.append(dict(issue_type="SLA_IGNORES_CALENDAR" if wall else "SLA_DEADLINE_MISMATCH", related_record_id=tid, severity="HIGH" if wall else "MEDIUM",
                              description=f"Stored due (response {rd}, resolution {sd}) differs from calendar-based due (response {fmt(er)}, resolution {fmt(es)})" + (" (stored value equals wall-clock addition)" if wall else "")))
    for tid, rc in conn.execute("SELECT ticket_id,reopen_count FROM ticket WHERE reopen_count>0"):
        cyc = [r[0] for r in conn.execute("SELECT cycle_no FROM resolution WHERE ticket_id=? ORDER BY cycle_no", (tid,))]
        nres = conn.execute("SELECT COUNT(*) FROM ticket_status_history WHERE ticket_id=? AND to_status='RESOLVED'", (tid,)).fetchone()[0]
        if cyc != list(range(1, len(cyc)+1)) or len(cyc) != nres:
            found.append(dict(issue_type="REOPEN_HISTORY_LOST", related_record_id=tid, severity="HIGH",
                              description=f"Reopened ticket has resolution cycles {cyc} but lifecycle shows {nres} resolutions."))
    chains = {}
    for tid, fr, to in conn.execute("SELECT ticket_id,from_agent_id,to_agent_id FROM assignment_event WHERE event_type='TRANSFER' ORDER BY ticket_id,seq"):
        chains.setdefault(tid, []).append((fr, to))
    for tid, ch in chains.items():
        seen = [ch[0][0]]
        for fr, to in ch:
            if to in seen:
                found.append(dict(issue_type="TRANSFER_LOOP", related_record_id=tid, severity="HIGH", description=f"Ticket returned to {to}: chain {seen + [to]}")); break
            seen.append(to)
    for tid, pr, tier, subj, body in conn.execute("""SELECT t.ticket_id,t.priority,c.tier,t.subject,m.body FROM ticket t JOIN customer c USING(customer_id)
                                                  JOIN message m ON m.ticket_id=t.ticket_id AND m.seq=1"""):
        text = subj + " " + body
        if any(k in text.lower() for k in rules.safety_keywords) and pr != "CRITICAL":
            found.append(dict(issue_type="SAFETY_PRIORITY_VIOLATION", related_record_id=tid, severity="CRITICAL",
                              description=f"Safety keyword present but priority is {pr}; safety rule requires CRITICAL."))
    return found

def inject_anomalies(conn, out_dir):
    """Inject exactly five labelled anomalies into a valid baseline. Returns ground-truth list (also written to out_dir)."""
    rules = RuleSet.from_db(conn); sla = rules.sla; gt = []
    def add(typ, rid, desc, sev, det, dec): gt.append(dict(anomaly_id=f"ANOM-{len(gt)+1:03d}", related_record_id=rid, issue_type=typ, description=desc, severity=sev, expected_detection=det, expected_decision=dec))
    # 4. transfer loop (first, to choose the ticket before other edits)
    cands = [r[0] for r in conn.execute("SELECT ticket_id FROM assignment_event WHERE event_type='TRANSFER' GROUP BY ticket_id HAVING COUNT(*)>=2 ORDER BY ticket_id")]
    iv = _agent_intervals(conn); caps = dict(conn.execute("SELECT agent_id,max_concurrent FROM agent")); done = False
    for tid in cands:
        ev = conn.execute("SELECT assignment_id,from_agent_id,to_agent_id,event_at_utc,released_at_utc FROM assignment_event WHERE ticket_id=? AND event_type IN ('ASSIGN','TRANSFER') ORDER BY seq", (tid,)).fetchall()
        first, last = ev[0][2], ev[-1]
        if last[2] == first: continue
        s, e = parse(last[3]), parse(last[4]) if last[4] else _asof(conn)
        busy = max([sum(1 for (a, b, _) in iv.get(first, []) if a < e and b > s)] + [0])
        shifts = {}
        for d, a, b in conn.execute("SELECT weekday,start_min_utc,end_min_utc FROM agent_shift WHERE agent_id=?", (first,)): shifts.setdefault(d, []).append((a, b))
        if busy < caps[first] and shift_remaining(shifts, s) > 0:
            conn.execute("UPDATE assignment_event SET to_agent_id=? WHERE assignment_id=?", (first, last[0]))
            conn.execute("UPDATE ticket SET current_agent_id=CASE WHEN current_agent_id=? THEN ? ELSE current_agent_id END WHERE ticket_id=?", (last[2], first, tid))
            conn.execute("UPDATE resolution SET resolved_by_agent_id=? WHERE ticket_id=? AND resolved_by_agent_id=?", (first, tid, last[2]))
            conn.execute("UPDATE message SET sender_agent_id=? WHERE ticket_id=? AND sender_agent_id=?", (first, tid, last[2]))
            add("TRANSFER_LOOP", tid, f"Ticket transferred back to {first} after passing through other agents.", "HIGH", "Repeated agent in transfer chain", "Flag for supervisor review; block further transfers"); done = True; break
    assert done, "no suitable ticket for transfer-loop injection"
    # 1. capacity: agent whose peak concurrency K>=2 gets an effective limit of K-1
    best = None
    for ag, ivs in sorted(iv.items()):
        active, peak, first = [], 0, None
        for s_, e_, aid in sorted(ivs):
            active = [x for x in active if x > s_]; active.append(e_)
            if len(active) > peak: peak, first = len(active), aid
        if peak >= 2 and (best is None or peak > best[1]): best = (ag, peak, first)
    assert best, "no agent with concurrency >= 2"
    ag, peak, _ = best; conn.execute("UPDATE agent SET max_concurrent=? WHERE agent_id=?", (peak-1, ag))
    first_viol = capacity_violations(conn)[ag][0]
    add("CAPACITY_EXCEEDED", first_viol, f"Agent {ag} (limit {peak-1}) was assigned {peak} simultaneous tickets.", "HIGH", "Concurrent assignments exceed agent max_concurrent", "Reject assignment; re-route to an agent with spare capacity")
    # 2. SLA ignoring channel calendar
    for tid, ch, pr, cr in conn.execute("SELECT ticket_id,channel_id,priority,created_at_utc FROM ticket WHERE channel_id='EMAIL' AND priority IN ('LOW','MEDIUM') ORDER BY ticket_id"):
        c = parse(cr); tr, ts = sla.targets(ch, pr); er, es = sla.deadlines(ch, pr, c)
        if abs((er - (c + timedelta(minutes=tr))).total_seconds()) > 3600 and abs((es - (c + timedelta(minutes=ts))).total_seconds()) > 3600:
            wr, ws = fmt(c + timedelta(minutes=tr)), fmt(c + timedelta(minutes=ts))
            conn.execute("UPDATE ticket SET sla_response_due_utc=?, sla_resolution_due_utc=? WHERE ticket_id=?", (wr, ws, tid))
            conn.execute("UPDATE sla_event SET due_at_utc=? WHERE ticket_id=? AND event_type='START' AND target_type='RESPONSE'", (wr, tid))
            conn.execute("UPDATE sla_event SET due_at_utc=? WHERE ticket_id=? AND event_type='START' AND target_type='RESOLUTION'", (ws, tid))
            add("SLA_IGNORES_CALENDAR", tid, "Deadlines computed as created_at + target hours, ignoring the EMAIL business calendar.", "HIGH", "Recomputed calendar deadline differs from stored deadline", "Recalculate SLA with channel calendar"); break
    # 3. reopened ticket loses history
    r = conn.execute("""SELECT t.ticket_id FROM ticket t WHERE reopen_count=1 AND status IN ('RESOLVED','CLOSED') AND
                        (SELECT COUNT(*) FROM resolution r WHERE r.ticket_id=t.ticket_id)=2 ORDER BY ticket_id""").fetchone()
    assert r, "no reopened ticket with two cycles"
    conn.execute("DELETE FROM resolution WHERE ticket_id=? AND cycle_no=1", (r[0],))
    add("REOPEN_HISTORY_LOST", r[0], "First resolution record was deleted when the ticket was reopened.", "HIGH", "Resolution cycles not contiguous / fewer than lifecycle RESOLVED events", "Restore resolution history from audit trail")
    # 5. safety priority contradiction
    r = conn.execute("""SELECT t.ticket_id,t.channel_id FROM ticket t WHERE safety_flag=1 AND priority='CRITICAL' AND intent_id='PRODUCT_SAFETY' ORDER BY ticket_id LIMIT 1 OFFSET 2""").fetchone() or \
        conn.execute("SELECT ticket_id,channel_id FROM ticket WHERE safety_flag=1 AND priority='CRITICAL' ORDER BY ticket_id").fetchone()
    tid, ch = r; cr = parse(conn.execute("SELECT created_at_utc FROM ticket WHERE ticket_id=?", (tid,)).fetchone()[0])
    rd, sd = sla.deadlines(ch, "LOW", cr)
    conn.execute("UPDATE ticket SET priority='LOW', sla_response_due_utc=?, sla_resolution_due_utc=? WHERE ticket_id=?", (fmt(rd), fmt(sd), tid))
    conn.execute("UPDATE sla_event SET due_at_utc=? WHERE ticket_id=? AND event_type='START' AND target_type='RESPONSE'", (fmt(rd), tid))
    conn.execute("UPDATE sla_event SET due_at_utc=? WHERE ticket_id=? AND event_type='START' AND target_type='RESOLUTION'", (fmt(sd), tid))
    add("SAFETY_PRIORITY_VIOLATION", tid, "Ticket describes overheating/smoke/fire but was stored with priority LOW.", "CRITICAL", "Safety keyword present and priority != CRITICAL", "Escalate to CRITICAL and Safety queue immediately")
    conn.commit()
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir/"ground_truth.json").write_text(json.dumps(gt, indent=2), encoding="utf-8")
    with open(out_dir/"ground_truth.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(gt[0])); w.writeheader(); w.writerows(gt)
    return gt

def evaluate_detection(detected, gt):
    """Compare detector output with ground truth (evaluation only)."""
    key = {(d["issue_type"], d["related_record_id"]) for d in detected}
    res = [dict(anomaly_id=g["anomaly_id"], issue_type=g["issue_type"], related_record_id=g["related_record_id"], detected=(g["issue_type"], g["related_record_id"]) in key) for g in gt]
    gk = {(g["issue_type"], g["related_record_id"]) for g in gt}
    extra = [d for d in detected if (d["issue_type"], d["related_record_id"]) not in gk]
    return res, extra
