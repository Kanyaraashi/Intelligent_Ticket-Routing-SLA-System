"""Generates docs/DATA_DICTIONARY.md and the Mermaid ER diagram directly from the real schema."""
import _boot, re, sqlite3
from src import db
DESC = {"ticket_id":"Business key TKT-2026-NNNNNN","customer_id":"CUS-NNNNNN","agent_id":"AGT-NNNNNN","message_id":"MSG-<ticket_id>-NNN","assignment_id":"ASN-<ticket_id>-NNN",
 "sla_event_id":"SLA-<ticket_id> (first event) then SLA-<ticket_id>-NN","resolution_id":"RES-<ticket_id>-CC (CC = resolution cycle)","priority":"Business priority; safety rules force CRITICAL",
 "status":"Lifecycle state","current_agent_id":"Agent currently responsible (NULL when waiting/resolved/closed)","created_at_utc":"UTC creation time","first_response_at_utc":"Time of first agent message (derived)",
 "resolved_at_utc":"Latest resolution time (derived from resolution)","sla_response_due_utc":"Calendar-aware response deadline","sla_resolution_due_utc":"Calendar-aware resolution deadline (extended by SLA pauses)",
 "reopen_count":"Number of REOPENED transitions (derived)","transfer_count":"Number of TRANSFER assignment events (derived)","is_escalated":"1 if ever escalated","safety_flag":"1 if safety rule matched at routing time",
 "max_concurrent":"Maximum simultaneous tickets (hard capacity limit)","released_at_utc":"When the agent stopped holding the ticket (NULL = still open)","decision_json":"Explainable routing decision: rejections, top candidates and score parts",
 "reason_code":"Why the event happened (e.g. ROUTED_BEST_SCORE, NO_AGENT_ON_SHIFT, WAIT_THRESHOLD_EXCEEDED, TRANSFER:SKILL_GAP)","score":"Routing score 0-100","use_24x7":"1 = critical priority uses 24x7 calendar",
 "response_target_min":"Target in WORKING minutes","resolution_target_min":"Target in WORKING minutes","csat_score":"Customer satisfaction 1-5 (optional survey)","effective_from":"Start of validity","effective_to":"End of validity (NULL = open-ended)",
 "work_days":"Comma list of weekdays, Monday=0","open_min_utc":"Opening minute of day (UTC)","close_min_utc":"Closing minute of day (UTC)","keywords":"JSON list of classifier keywords","proficiency":"1 (basic) to 5 (expert)"}
c = sqlite3.connect(":memory:"); db.init_schema(c); sql = (db.ROOT/"database"/"schema.sql").read_text()
out = ["# Data Dictionary", "Generated from `database/schema.sql` by `scripts/build_data_dictionary.py`. All timestamps are UTC text `YYYY-MM-DDTHH:MM:SSZ`.", ""]
er = ["```mermaid", "erDiagram"]
for (t,) in c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY rowid").fetchall():
    body = re.search(rf"CREATE TABLE {t} \((.*?)\n?\);", sql, re.S).group(1)
    fks = {r[3]: (r[2], r[4]) for r in c.execute(f"PRAGMA foreign_key_list({t})")}
    out += [f"## {t}", "", "| Column | Type | Key | Required | Allowed values / rule | Description |", "|---|---|---|---|---|---|"]
    for cid, n, ty, nn, d, pk in c.execute(f"PRAGMA table_info({t})"):
        m = re.search(rf"{n}[^,]*?CHECK \({n} IN \(([^)]*)\)\)", body) or re.search(rf"CHECK \({n} IN \(([^)]*)\)\)", body)
        allowed = m.group(1).replace("'", "") if m else (re.search(rf"{n}[^,]*CHECK \(({n} BETWEEN [^)]*)\)", body).group(1) if re.search(rf"{n}[^,]*CHECK \(({n} BETWEEN [^)]*)\)", body) else "")
        key = ("PK " if pk else "") + (f"FK->{fks[n][0]}" if n in fks else "")
        out.append(f"| {n} | {ty} | {key.strip()} | {'yes' if nn or pk else 'no'} | {allowed} | {DESC.get(n, '')} |")
    out.append("")
    er.append(f"  {t} {{"); [er.append(f"    {r[2] or 'TEXT'} {r[1]}" + (" PK" if r[5] else "")) for r in c.execute(f"PRAGMA table_info({t})")]; er.append("  }")
for (t,) in c.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY rowid").fetchall():
    for r in c.execute(f"PRAGMA foreign_key_list({t})"): er.append(f"  {r[2]} ||--o{{ {t} : \"{r[3]}\"")
er.append("```")
(db.ROOT/"docs"/"DATA_DICTIONARY.md").write_text("\n".join(out), encoding="utf-8")
(db.ROOT/"docs"/"ER_DIAGRAM.md").write_text("# ER Diagram (Mermaid)\n\n" + "\n".join(er) + "\n", encoding="utf-8"); print("ok")
