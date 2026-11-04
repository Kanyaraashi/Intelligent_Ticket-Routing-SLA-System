import sys, json
from datetime import datetime, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import pandas as pd, plotly.express as px, streamlit as st
from src import db, metrics, simulation
from src.validation import validate, summarize
from src.anomalies import detect_anomalies, evaluate_detection
from src.timeutil import parse

st.set_page_config(page_title="Ticket Routing & SLA", page_icon=":ticket:", layout="wide")
ROOT = Path(__file__).resolve().parent
dbs = [p for p in ("starter", "full") if (ROOT/"data"/f"{p}.db").exists()]
if not dbs:
    st.error("No database found. Run GENERATE_STARTER_DATA.bat first."); st.stop()

st.markdown("""
<style>
    [data-testid="stAppViewContainer"] {
        background: linear-gradient(180deg, #f7f9fc 0%, #eef3f8 100%);
    }
    [data-testid="stHeader"] { background: transparent; }
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #10233f 0%, #173a63 100%);
    }
    [data-testid="stSidebar"] * { color: #f4f7fb !important; }
    [data-testid="stSidebar"] [role="radiogroup"] label {
        border-radius: 8px;
        padding: 4px 8px;
        margin-bottom: 2px;
    }
    [data-testid="stSidebar"] [role="radiogroup"] label:hover {
        background: rgba(255,255,255,0.09);
    }
    [data-testid="stMetric"] {
        background: #ffffff;
        border: 1px solid #dfe7f1;
        border-radius: 14px;
        padding: 16px;
        box-shadow: 0 4px 16px rgba(23, 58, 99, 0.07);
    }
    [data-testid="stDataFrame"] {
        border: 1px solid #dfe7f1;
        border-radius: 12px;
        overflow: hidden;
        background: white;
    }
    .project-hero {
        padding: 28px 32px;
        border-radius: 18px;
        color: white;
        background: linear-gradient(135deg, #173a63 0%, #2563a9 55%, #1ea7a1 100%);
        box-shadow: 0 12px 30px rgba(23,58,99,0.18);
        margin-bottom: 18px;
    }
    .project-hero h1 { margin: 0 0 8px 0; color: white; font-size: 2rem; }
    .project-hero p { margin: 0; color: #edf6ff; font-size: 1rem; }
    .info-card {
        height: 100%;
        background: white;
        border: 1px solid #dfe7f1;
        border-radius: 14px;
        padding: 18px;
        color: #263b53;
        box-shadow: 0 4px 16px rgba(23,58,99,0.06);
    }
    .info-card h3 { margin-top: 0; color: #173a63; }
    .info-card li { color: #263b53; }
    [data-testid="stMarkdownContainer"] { color: #263b53; }
    [data-testid="stMarkdownContainer"] h1,
    [data-testid="stMarkdownContainer"] h2,
    [data-testid="stMarkdownContainer"] h3,
    [data-testid="stMarkdownContainer"] h4 { color: #173a63; }
    .step-card {
        border-left: 4px solid #1ea7a1;
        background: white;
        border-radius: 0 12px 12px 0;
        padding: 14px 18px;
        margin-bottom: 10px;
        color: #263b53;
        box-shadow: 0 3px 12px rgba(23,58,99,0.05);
    }
    .step-card strong { color: #173a63; }
    div.stButton > button[kind="primary"] {
        border-radius: 10px;
        padding: 0.55rem 1rem;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

st.sidebar.markdown("""
<div style="padding: 8px 2px 16px 2px;">
  <div style="font-size: 1.3rem; font-weight: 700;">Ticket Operations</div>
  <div style="font-size: 0.82rem; opacity: 0.78;">Routing, SLA &amp; quality intelligence</div>
</div>
""", unsafe_allow_html=True)
mode = st.sidebar.selectbox("Dataset", dbs)
PAGES = ["Executive Overview", "Ticket Explorer", "Intelligent Routing", "Agent Performance", "SLA Monitoring", "Queue Analytics", "Anomaly Detection", "Data Validation", "About the Project"]
page = st.sidebar.radio("Workspace", PAGES)

@st.cache_resource
def conn_for(m): return db.connect(ROOT/"data"/f"{m}.db", readonly=True)
conn = conn_for(mode)
@st.cache_data(show_spinner=False)
def q(m, sql, params=()): return pd.read_sql(sql, conn_for(m), params=params)
@st.cache_data(show_spinner=False)
def get_kpis(m): return metrics.kpis(conn_for(m))
@st.cache_data(show_spinner=False)
def get_validation(m): return validate(conn_for(m))
def dl(df, name): st.download_button(f"Download {name}.csv", df.to_csv(index=False).encode(), f"{name}.csv", "text/csv")
st.sidebar.caption(f"Data as of {get_kpis(mode)['as_of_utc']} (UTC)")

if page == "Executive Overview":
    st.title("Executive Overview"); k = get_kpis(mode)
    r1 = st.columns(5); r2 = st.columns(5); r3 = st.columns(5)
    for c, (l, v) in zip(r1 + r2 + r3, [("Total tickets", f"{k['total_tickets']:,}"), ("Resolved", f"{k['resolved_tickets']:,}"), ("Open", f"{k['open_tickets']:,}"), ("Unassigned (open)", f"{k['unassigned_tickets']:,}"),
        ("Avg first response (min)", f"{k['avg_first_response_min']:.1f}"), ("Avg resolution (min)", f"{k['avg_resolution_min']:.0f}"), ("SLA compliance", f"{k['sla_compliance_pct']:.1f}%"), ("SLA breaches", f"{k['sla_breaches']:,}"),
        ("Escalations", f"{k['escalations']:,}"), ("Reopening rate", f"{k['reopening_rate_pct']:.1f}%"), ("Transfers", f"{k['transfers']:,}"), ("Avg agent utilization", f"{k['avg_agent_utilization_pct']:.1f}%"),
        ("Routing success", f"{k['routing_success_rate_pct']:.1f}%"), ("Avg queue wait (min)", f"{k['avg_queue_wait_min']:.1f}"), ("Avg CSAT", f"{k['avg_csat']:.2f}")]): c.metric(l, v)
    st.caption(f"Skill mismatches: {k['skill_mismatches']} | Language mismatches: {k['language_mismatches']} | Capacity violations: {k['capacity_violations']}")
    d = q(mode, "SELECT substr(created_at_utc,1,10) day, channel_id, COUNT(*) tickets FROM ticket GROUP BY 1,2")
    st.plotly_chart(px.bar(d, x="day", y="tickets", color="channel_id", title="Tickets per day by channel"), width="stretch")
    c1, c2 = st.columns(2)
    c1.plotly_chart(px.pie(q(mode, "SELECT status, COUNT(*) n FROM ticket GROUP BY 1"), names="status", values="n", title="Ticket status"), width="stretch")
    c2.plotly_chart(px.bar(q(mode, "SELECT intent_id, priority, COUNT(*) n FROM ticket GROUP BY 1,2"), x="intent_id", y="n", color="priority", title="Intent and priority"), width="stretch")

elif page == "Ticket Explorer":
    st.title("Ticket Explorer")
    f = st.columns(5); status = f[0].multiselect("Status", ["NEW","OPEN","ASSIGNED","IN_PROGRESS","PENDING_CUSTOMER","RESOLVED","CLOSED","REOPENED","ESCALATED"])
    chn = f[1].multiselect("Channel", ["EMAIL","CHAT","PHONE"]); pri = f[2].multiselect("Priority", ["LOW","MEDIUM","HIGH","CRITICAL"])
    lang = f[3].multiselect("Language", q(mode, "SELECT language_code FROM language").language_code.tolist()); text = f[4].text_input("Search (ID, subject, customer)")
    df = q(mode, "SELECT t.ticket_id,t.created_at_utc,t.channel_id,t.intent_id,t.language_code,t.queue_id,t.priority,t.status,t.current_agent_id,t.subject,c.name customer,t.reopen_count,t.transfer_count,t.is_escalated FROM ticket t JOIN customer c USING(customer_id) ORDER BY t.ticket_id")
    for col, val in [("status", status), ("channel_id", chn), ("priority", pri), ("language_code", lang)]:
        if val: df = df[df[col].isin(val)]
    if text: df = df[df.apply(lambda r: text.lower() in (r.ticket_id + r.subject + r.customer).lower(), axis=1)]
    st.write(f"{len(df):,} tickets"); st.dataframe(df.head(2000), width="stretch", hide_index=True); dl(df, "tickets")
    tid = st.text_input("Open ticket ID", df.ticket_id.iloc[0] if len(df) else "")
    if tid:
        for title, sql in [("Assignment history and routing decisions", "SELECT assignment_id,event_type,from_agent_id,to_agent_id,event_at_utc,released_at_utc,reason_code,score,decision_json FROM assignment_event WHERE ticket_id=? ORDER BY seq"),
                           ("Lifecycle", "SELECT seq,from_status,to_status,changed_at_utc,actor_type,reason FROM ticket_status_history WHERE ticket_id=? ORDER BY seq"),
                           ("Messages", "SELECT seq,sender_type,sender_agent_id,sent_at_utc,body FROM message WHERE ticket_id=? ORDER BY seq"),
                           ("SLA events", "SELECT sla_event_id,event_type,target_type,due_at_utc,occurred_at_utc,details FROM sla_event WHERE ticket_id=? ORDER BY seq"),
                           ("Resolutions", "SELECT * FROM resolution WHERE ticket_id=? ORDER BY cycle_no")]:
            st.subheader(title); st.dataframe(q(mode, sql, (tid,)), width="stretch", hide_index=True)

elif page == "Intelligent Routing":
    st.title("Intelligent Routing - simulation mode")
    st.info("Simulation is read-only: the database is opened read-only, so persisted ticket history can never be changed here.")
    a, b = st.columns(2)
    ch = a.selectbox("Channel", ["EMAIL", "CHAT", "PHONE"]); lg = a.selectbox("Customer language", q(mode, "SELECT language_code FROM language").language_code.tolist())
    tier = a.selectbox("Customer tier", ["STANDARD", "GOLD", "PLATINUM"])
    sub = b.text_input("Subject", "Charger overheating"); body = b.text_area("Message", "My charger is overheating and there was smoke from the plug.")
    d0 = parse(get_kpis(mode)["as_of_utc"]); day = a.date_input("Arrival date (UTC)", d0.date()); tm = a.time_input("Arrival time (UTC)", time(10, 0))
    if st.button("Route this ticket", type="primary"):
        r = simulation.simulate(conn, ch, lg, tier, sub, body, datetime.combine(day, tm)); dd = r["decision"]
        c = st.columns(4); c[0].metric("Intent", r["intent"]); c[1].metric("Priority", r["priority"]); c[2].metric("Queue", r["queue"]); c[3].metric("Selected agent", dd.agent_id or "NONE")
        st.write(f"**Rules applied:** {r['rules_applied'] or 'none'} | **Required skills:** {r['required_skills']} | **Safety rule:** {r['safety']}")
        st.write(f"**Response due:** {r['response_due']} | **Resolution due:** {r['resolution_due']} | **Escalation due (if unassigned):** {r['escalation_due']}")
        if dd.agent_id: st.success(f"Assigned to {dd.agent_id} (score {dd.score}). Reason: {dd.reason_code}")
        else: st.warning(f"No agent available -> ticket stays in {r['queue']}. Reason: {dd.reason_code}")
        st.subheader("Eligible agents (ranked)"); st.dataframe(pd.DataFrame([{**{"agent_id": c_["agent_id"], "score": c_["score"]}, **c_["breakdown"]} for c_ in dd.candidates]), width="stretch", hide_index=True)
        st.subheader("Rejected agents and reasons"); rj = pd.DataFrame([{"agent_id": a_, "reasons": ", ".join(w)} for a_, w in dd.rejected]); st.dataframe(rj, width="stretch", hide_index=True)
        if len(rj): st.plotly_chart(px.bar(rj.assign(r=rj.reasons.str.split(", ")).explode("r").assign(r=lambda x: x.r.str.split(":").str[0]).groupby("r").size().reset_index(name="agents"), x="r", y="agents", title="Why agents were rejected"), width="stretch")

elif page == "Agent Performance":
    st.title("Agent Performance"); ap = metrics.agent_performance(conn); st.dataframe(ap.round(2), width="stretch", hide_index=True); dl(ap, "agent_performance")
    st.plotly_chart(px.bar(ap.sort_values("utilization_pct", ascending=False).head(40), x="agent_id", y="utilization_pct", color="shift_pattern", title="Agent utilization % (held ticket-hours / shift capacity)"), width="stretch")
    st.plotly_chart(px.scatter(ap, x="utilization_pct", y="avg_csat", size="resolved", hover_name="agent_id", title="Utilization vs CSAT"), width="stretch")

elif page == "SLA Monitoring":
    st.title("SLA Monitoring"); s = metrics.sla_table(conn); k = get_kpis(mode)
    c = st.columns(4); c[0].metric("Compliance", f"{k['sla_compliance_pct']:.1f}%"); c[1].metric("Response breaches", k["response_breaches"]); c[2].metric("Resolution breaches", k["resolution_breaches"]); c[3].metric("Escalations", k["escalations"])
    g = s.assign(breach=s.resp_breach | s.res_breach).groupby(["channel_id", "priority"]).breach.mean().mul(100).reset_index(name="breach_pct")
    st.plotly_chart(px.bar(g, x="priority", y="breach_pct", color="channel_id", barmode="group", title="Breach rate % by priority and channel"), width="stretch")
    st.subheader("Business calendars"); st.dataframe(q(mode, "SELECT channel_id,work_days,open_min_utc/60.0 open_hour_utc,close_min_utc/60.0 close_hour_utc FROM channel"), hide_index=True)
    st.dataframe(q(mode, "SELECT * FROM holiday"), hide_index=True); st.subheader("Inspect a ticket's SLA")
    tid = st.text_input("Ticket ID", "TKT-2026-000001")
    st.dataframe(q(mode, "SELECT ticket_id,channel_id,priority,created_at_utc,sla_response_due_utc,sla_resolution_due_utc FROM ticket WHERE ticket_id=?", (tid,)), hide_index=True)
    st.dataframe(q(mode, "SELECT event_type,target_type,due_at_utc,occurred_at_utc,details FROM sla_event WHERE ticket_id=? ORDER BY seq", (tid,)), hide_index=True)
    br = s[s.resp_breach | s.res_breach]; st.write(f"{len(br):,} breached tickets"); st.dataframe(br.head(500), width="stretch", hide_index=True); dl(br, "sla_breaches")

elif page == "Queue Analytics":
    st.title("Queue Analytics"); w = metrics.queue_wait(conn)
    st.plotly_chart(px.box(w, x="queue_id", y="wait_min", color="priority", title="Wait until first assignment (min)"), width="stretch")
    g = w.groupby("queue_id").wait_min.agg(["count", "mean", "median", "max"]).round(1).reset_index(); st.dataframe(g, hide_index=True); dl(g, "queue_waits")
    st.plotly_chart(px.bar(q(mode, "SELECT queue_id, reason_code, COUNT(*) n FROM assignment_event WHERE event_type='UNASSIGNED' GROUP BY 1,2"), x="queue_id", y="n", color="reason_code", title="Why tickets waited (UNASSIGNED reasons)"), width="stretch")
    st.plotly_chart(px.line(q(mode, "SELECT substr(created_at_utc,1,13) hour, COUNT(*) tickets FROM ticket GROUP BY 1"), x="hour", y="tickets", title="Hourly arrivals (spikes visible)"), width="stretch")

elif page == "Anomaly Detection":
    st.title("Anomaly Detection"); det = detect_anomalies(conn); df = pd.DataFrame(det); st.write(f"Detector found **{len(df)}** rule violations (it never reads ground truth)."); st.dataframe(df, width="stretch", hide_index=True)
    gt = ROOT/"data"/f"ground_truth_{mode}"/"ground_truth.json"
    if gt.exists():
        st.subheader("Evaluation against ground truth (evaluation only)"); g = json.loads(gt.read_text()); res, extra = evaluate_detection(det, g)
        st.dataframe(pd.DataFrame(res), hide_index=True); st.write(f"Detected {sum(r['detected'] for r in res)} of {len(res)} injected anomalies; extra detections: {len(extra)}"); st.dataframe(pd.DataFrame(g), hide_index=True)
    if len(df): dl(df, "anomalies")

elif page == "Data Validation":
    st.title("Data Validation"); iss = get_validation(mode); sm = summarize(iss); st.dataframe(sm, hide_index=True, width="stretch")
    st.write(f"Total issues: **{len(iss)}**"); df = pd.DataFrame(iss); st.dataframe(df, width="stretch", hide_index=True)
    if len(df): dl(df, "validation_issues")

else:
    st.markdown("""
    <div class="project-hero">
      <h1>Intelligent Ticket Operations</h1>
      <p>Explainable routing + service-level protection for high-volume, multi-channel support teams.</p>
    </div>
    """, unsafe_allow_html=True)

    overview, modern_problem, impact = st.tabs(["How the Project Works", "Modern Problem It Solves", "Project Impact"])

    with overview:
        st.markdown("""
        <div class="step-card"><strong>1. Ticket intake</strong><br>
        Email, chat and phone requests are stored with customer, language, channel, intent, priority and arrival time.</div>
        <div class="step-card"><strong>2. Explainable classification</strong><br>
        The rules engine reads the subject and first message, identifies the intent, applies priority and safety rules, and selects the queue and required skills. Safety keywords such as smoke or overheating cannot be downgraded.</div>
        <div class="step-card"><strong>3. Intelligent agent selection</strong><br>
        Hard constraints remove agents who are inactive, off shift, unable to speak the language, lack a skill, or have reached capacity. Remaining agents receive a transparent score based on availability, shift runway, proficiency and continuity.</div>
        <div class="step-card"><strong>4. SLA and lifecycle management</strong><br>
        Business calendars calculate working-time deadlines, including nights, weekends and holidays. Customer pauses adjust resolution deadlines while status transitions and escalations are recorded in history.</div>
        <div class="step-card"><strong>5. Outcome intelligence</strong><br>
        SQLite and Pandas power operational dashboards, while the anomaly detector flags transfers loops, capacity failures, calendar mistakes, lost reopen history and unsafe priority handling.</div>
        """, unsafe_allow_html=True)
        st.caption("The dashboard simulation uses the same routing function as data generation, but its database connection is read-only.")

        flow_cols = st.columns(4)
        flow_cols[0].metric("Input", "Email, chat & phone")
        flow_cols[1].metric("Decision", "Intent + priority + queue")
        flow_cols[2].metric("Assignment", "Rules + ranked agents")
        flow_cols[3].metric("Control", "SLA + lifecycle + audit")

    with modern_problem:
        st.markdown("""
        Support operations often mix up **volume, urgency, skill, language, availability and business-time deadlines**.
        Manual routing can create delays, repeated transfers, overload, missed commitments and inconsistent decisions.
        This project addresses those problems with a controlled, explainable workflow rather than treating every ticket as the same queue item.
        """)
        p1, p2 = st.columns(2)
        with p1:
            st.markdown("""
            <div class="info-card">
              <h3>Problems addressed</h3>
              <ul>
                <li>Wrongly assigned or repeatedly transferred tickets</li>
                <li>Overloaded agents and unbalanced workloads</li>
                <li>Missed response and resolution deadlines</li>
                <li>Unsafe customer issues receiving ordinary priority</li>
                <li>Hidden decisions that are difficult to audit</li>
              </ul>
            </div>
            """, unsafe_allow_html=True)
        with p2:
            st.markdown("""
            <div class="info-card">
              <h3>How this system helps</h3>
              <ul>
                <li>Matches customers with language, skill and shift coverage</li>
                <li>Balances available capacity instead of choosing by queue order</li>
                <li>Protects critical issues with 24x7 safety handling</li>
                <li>Records every assignment, rejection, deadline and transition</li>
                <li>Detects data and process failures before they become trends</li>
              </ul>
            </div>
            """, unsafe_allow_html=True)
        st.info("The system is a deterministic decision-support prototype. It does not replace human judgment; it provides consistent recommendations and makes the reason for each decision visible.")

    with impact:
        c1, c2, c3 = st.columns(3)
        c1.markdown("""
        <div class="info-card"><h3>Customer experience</h3>
        Faster first assignment, fewer transfers, language and skill fit, and deadlines measured against the customer's support calendar.</div>
        """, unsafe_allow_html=True)
        c2.markdown("""
        <div class="info-card"><h3>Operations teams</h3>
        Clear queue visibility, agent capacity awareness, reproducible rules, measurable bottlenecks and direct investigation tools.</div>
        """, unsafe_allow_html=True)
        c3.markdown("""
        <div class="info-card"><h3>Organizations</h3>
        Better SLA accountability, traceable decisions, data-quality controls and evidence for process improvement.</div>
        """, unsafe_allow_html=True)

        st.markdown("#### Why it matters now")
        st.write(
            "Modern support teams operate across channels, time zones and service tiers. "
            "They need to respond quickly while also protecting specialized expertise and contractual commitments. "
            "This project demonstrates how rule-based automation can combine speed, fairness, safety and auditability without requiring paid APIs or a cloud dependency."
        )
