"""Read-only routing simulation: what WOULD happen for a new ticket at a chosen time. Never writes to the database."""
from .rules import RuleSet
from .routing import AgentState, route
from .timeutil import fmt, parse

def load_agents(conn, at):
    ats = fmt(at); ag = {}
    for a, mx, st in conn.execute("SELECT agent_id,max_concurrent,status FROM agent ORDER BY agent_id"): ag[a] = AgentState(a, mx, {}, [], {}, 0, st)
    for a, s, p in conn.execute("SELECT agent_id,skill_id,proficiency FROM agent_skill"): ag[a].skills[s] = p
    for a, l, pr in conn.execute("SELECT agent_id,language_code,is_primary FROM agent_language ORDER BY is_primary DESC"): ag[a].languages.append(l)
    for a, d, s, e in conn.execute("SELECT agent_id,weekday,start_min_utc,end_min_utc FROM agent_shift"): ag[a].shifts.setdefault(d, []).append((s, e))
    for a, n in conn.execute("SELECT to_agent_id,COUNT(*) FROM assignment_event WHERE to_agent_id IS NOT NULL AND event_at_utc<=? AND (released_at_utc IS NULL OR released_at_utc>?) GROUP BY 1", (ats, ats)): ag[a].active = n
    return list(ag.values())

def simulate(conn, channel, language, tier, subject, body, at):
    rules = RuleSet.from_db(conn); text = subject + " " + body
    intent = rules.classify_intent(text); prio, applied, safe = rules.priority(intent, text, tier)
    skills = rules.required_skills(intent, safe); queue = rules.queue_for(intent, safe)
    rd, sd = rules.sla.deadlines(channel, prio, at); esc = rules.sla.escalation_due(channel, prio, at)
    d = route(dict(language=language, required_skills=skills), load_agents(conn, at), at, explain=True)
    return dict(intent=intent, priority=prio, rules_applied=applied, safety=safe, required_skills=skills, queue=queue,
                response_due=fmt(rd), resolution_due=fmt(sd), escalation_due=fmt(esc), decision=d)
