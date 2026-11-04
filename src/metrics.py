"""All KPIs are computed from database records. Nothing is hardcoded."""
import pandas as pd
from .timeutil import parse
from .anomalies import capacity_violations

def _one(conn, sql): return conn.execute(sql).fetchone()[0]

def kpis(conn):
    as_of = _one(conn, "SELECT value FROM dataset_meta WHERE key='as_of_utc'")
    total = _one(conn, "SELECT COUNT(*) FROM ticket")
    k = dict(total_tickets=total,
        resolved_tickets=_one(conn, "SELECT COUNT(*) FROM ticket WHERE status IN ('RESOLVED','CLOSED')"),
        open_tickets=_one(conn, "SELECT COUNT(*) FROM ticket WHERE status NOT IN ('RESOLVED','CLOSED')"),
        unassigned_tickets=_one(conn, "SELECT COUNT(*) FROM ticket WHERE status NOT IN ('RESOLVED','CLOSED') AND current_agent_id IS NULL"),
        avg_first_response_min=_one(conn, "SELECT AVG((julianday(first_response_at_utc)-julianday(created_at_utc))*1440) FROM ticket WHERE first_response_at_utc IS NOT NULL"),
        avg_resolution_min=_one(conn, "SELECT AVG((julianday(resolved_at_utc)-julianday(created_at_utc))*1440) FROM ticket WHERE resolved_at_utc IS NOT NULL"),
        escalations=_one(conn, "SELECT COUNT(*) FROM ticket WHERE is_escalated=1"),
        reopened_tickets=_one(conn, "SELECT COUNT(*) FROM ticket WHERE reopen_count>0"),
        transfers=_one(conn, "SELECT COUNT(*) FROM assignment_event WHERE event_type='TRANSFER'"),
        avg_csat=_one(conn, "SELECT AVG(csat_score) FROM resolution WHERE csat_score IS NOT NULL"),
        csat_responses=_one(conn, "SELECT COUNT(csat_score) FROM resolution"),
        capacity_violations=sum(v[1] for v in capacity_violations(conn).values()))
    k["reopening_rate_pct"] = 100*k["reopened_tickets"]/total if total else 0
    # SLA: breach if event BREACH exists or (no MET and as_of > due)
    sla = sla_table(conn)
    k["response_breaches"] = int(sla.resp_breach.sum()); k["resolution_breaches"] = int(sla.res_breach.sum())
    k["sla_breaches"] = int((sla.resp_breach | sla.res_breach).sum())
    k["sla_compliance_pct"] = 100*(1 - k["sla_breaches"]/total) if total else 0
    asg = _one(conn, "SELECT COUNT(DISTINCT ticket_id) FROM assignment_event WHERE to_agent_id IS NOT NULL")
    k["routing_success_rate_pct"] = 100*asg/total if total else 0
    wait = queue_wait(conn); k["avg_queue_wait_min"] = float(wait.wait_min.mean()) if len(wait) else 0
    k.update(skill_mismatches=_mismatch(conn, "skill"), language_mismatches=_mismatch(conn, "lang"))
    u = agent_utilization(conn); k["avg_agent_utilization_pct"] = float(u.utilization_pct.mean()) if len(u) else 0
    k["as_of_utc"] = as_of
    return k

def _mismatch(conn, kind):
    if kind == "lang":
        return _one(conn, """SELECT COUNT(*) FROM assignment_event a JOIN ticket t USING(ticket_id) WHERE a.to_agent_id IS NOT NULL AND
            NOT EXISTS (SELECT 1 FROM agent_language l WHERE l.agent_id=a.to_agent_id AND l.language_code=t.language_code)""")
    return _one(conn, """SELECT COUNT(*) FROM assignment_event a JOIN ticket t USING(ticket_id) JOIN intent_skill s ON s.intent_id=t.intent_id
        WHERE a.to_agent_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM agent_skill k WHERE k.agent_id=a.to_agent_id AND k.skill_id=s.skill_id)""")

def sla_table(conn):
    as_of = _one(conn, "SELECT value FROM dataset_meta WHERE key='as_of_utc'")
    df = pd.read_sql("""SELECT ticket_id,channel_id,priority,queue_id,status,created_at_utc,first_response_at_utc,resolved_at_utc,sla_response_due_utc,sla_resolution_due_utc,
        (SELECT MIN(resolved_at_utc) FROM resolution r WHERE r.ticket_id=t.ticket_id) first_res FROM ticket t""", conn)
    resp_ref = df.first_response_at_utc.fillna(as_of); res_ref = df.first_res.fillna(as_of)
    df["resp_breach"] = resp_ref > df.sla_response_due_utc
    df["res_breach"] = res_ref > df.sla_resolution_due_utc
    return df

def queue_wait(conn):
    return pd.read_sql("""SELECT t.ticket_id,t.queue_id,t.priority,t.channel_id,(julianday(MIN(a.event_at_utc))-julianday(t.created_at_utc))*1440 AS wait_min
        FROM ticket t JOIN assignment_event a ON a.ticket_id=t.ticket_id AND a.to_agent_id IS NOT NULL GROUP BY t.ticket_id""", conn)

def agent_utilization(conn):
    """utilization = ticket-hours held / (shift-hours available x max_concurrent) over the dataset window."""
    meta = dict(conn.execute("SELECT key,value FROM dataset_meta").fetchall()); s, e = parse(meta["start_utc"]), parse(meta["as_of_utc"]); days = max((e - s).days, 1)
    df = pd.read_sql("""SELECT g.agent_id,g.name,g.max_concurrent,g.shift_pattern,
        COALESCE((SELECT SUM((julianday(COALESCE(a.released_at_utc,:e))-julianday(a.event_at_utc))*24) FROM assignment_event a WHERE a.to_agent_id=g.agent_id),0) held_hours,
        (SELECT COUNT(*) FROM assignment_event a WHERE a.to_agent_id=g.agent_id) assignments,
        (SELECT SUM(end_min_utc-start_min_utc) FROM agent_shift h WHERE h.agent_id=g.agent_id)/60.0 weekly_shift_hours
        FROM agent g""", conn, params={"e": meta["as_of_utc"]})
    df["shift_hours"] = df.weekly_shift_hours*days/7
    df["utilization_pct"] = 100*df.held_hours/(df.shift_hours*df.max_concurrent)
    return df

def agent_performance(conn):
    u = agent_utilization(conn)
    r = pd.read_sql("SELECT resolved_by_agent_id agent_id,COUNT(*) resolved,AVG(csat_score) avg_csat FROM resolution GROUP BY 1", conn)
    return u.merge(r, on="agent_id", how="left").fillna({"resolved": 0})
