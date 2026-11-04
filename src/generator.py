"""Deterministic synthetic data generator + event-driven simulation (routing, SLA, lifecycle). Seed 20261022."""
import heapq, itertools, json, math, random
from datetime import datetime, timedelta
from config.reference_data import *
from . import db
from .rules import RuleSet
from .routing import AgentState, route
from .lifecycle import assert_transition
from .timeutil import fmt

FIRST = "Ana Ben Chloe Dev Elif Farah Greg Hana Ivan Jia Kofi Lena Mohan Nia Omar Priya Quinn Rosa Sven Tara Uma Vik Wen Xena Yusuf Zoe".split()
LAST = "Silva Khan Moreau Reddy Schmidt Garcia Nguyen Brown Patel Costa Weber Rossi Singh Lopez Kim Fischer Iyer Santos Meyer Roy".split()
PATTERNS = {"MORNING": (300, 780), "DAY": (540, 1020), "EVENING": (780, 1260), "NIGHT": (1260, 300)}
HOURLY = [.2,.15,.1,.1,.15,.3,.6,1,1.5,1.8,1.9,1.7,1.4,1.6,1.8,1.7,1.5,1.2,.9,.7,.5,.4,.3,.25]
DOW = [1, 1.05, 1, 1, .95, .5, .4]

def tid(n): return f"TKT-2026-{n:06d}"

def build_agents(rng, n, start):
    quotas = {"SAFETY": max(2, round(n*.05)), "BILLING": round(n*.22), "ACCOUNT": round(n*.17), "LOGISTICS": round(n*.14),
              "GENERAL": round(n*.12), "RETENTION": max(2, round(n*.06))}
    quotas["TECHNICAL"] = n - sum(quotas.values())
    prim = [s for s, q in quotas.items() for _ in range(q)]; rng.shuffle(prim)
    pats = [p for p, w in zip(PATTERNS, (3, 3, 2, 2)) for _ in range(w)]
    offs = [(5, 6), (6, 0), (5, 6), (4, 5), (0, 1), (1, 2), (5, 6)]
    agents = []
    nonen = [l for l, _, _ in LANGUAGES if l != "en"]
    for i in range(n):
        sk = {prim[i]: rng.randint(3, 5)}
        if prim[i] == "SAFETY": sk["TECHNICAL"] = rng.randint(3, 5)
        else:
            for s in rng.sample([x for x, _ in SKILLS if x not in ("SAFETY", prim[i])], rng.choice([0, 1, 1, 2])): sk[s] = rng.randint(2, 4)
        langs = ["en"] if rng.random() < .65 else [rng.choice(nonen), "en"]
        if rng.random() < .25: langs.append(rng.choice([l for l in nonen if l not in langs]))
        pat, off = pats[i % len(pats)], offs[rng.randrange(len(offs))]
        agents.append(dict(agent_id=f"AGT-{i+1:06d}", name=f"{rng.choice(FIRST)} {rng.choice(LAST)}", max_concurrent=rng.choice([3, 4, 4, 5, 6]),
                           skills=sk, langs=langs, pattern=pat, off=off, hired=f"{rng.randint(2019, 2025)}-{rng.randint(1, 12):02d}-{rng.randint(1, 28):02d}"))
    # coverage repair: every (language, intent skill-set) must have a qualified agent
    sets = [set(i["skills"]) for i in INTENTS.values()]
    for l in nonen:
        for need in sets:
            if not any(l in a["langs"] and need <= set(a["skills"]) for a in agents):
                cand = sorted([a for a in agents if need <= set(a["skills"])], key=lambda a: (len(a["langs"]), a["agent_id"]))
                cand[0]["langs"].insert(1, l)
    for a in agents:
        rows = []
        for d in range(7):
            if d in a["off"]: continue
            s, e = PATTERNS[a["pattern"]]
            if a["pattern"] == "NIGHT": rows += [(d, 1260, 1440), ((d+1) % 7, 0, 300)]
            else: rows.append((d, s, e))
        a["shifts"] = rows
    return agents

def agent_state(a):
    sh = {}
    for d, s, e in a["shifts"]: sh.setdefault(d, []).append((s, e))
    return AgentState(a["agent_id"], a["max_concurrent"], a["skills"], a["langs"], sh)

def make_arrivals(rng, cfg, start):
    N, days = cfg["tickets"], cfg["days"]
    ch_ids = [c[0] for c in CHANNELS]; ch_w = [c[5] for c in CHANNELS]
    spike_tix = int(N*.08); spikes = []
    for k in range(cfg["spikes"] + cfg["incidents"]):
        spikes.append(dict(day=rng.randrange(1, days) if days > 1 else 0, hour=rng.randrange(8, 18), incident=k >= cfg["spikes"]))
    out = []
    # base slots per channel
    slots = {}
    for c in ch_ids:
        w = []
        for d in range(days):
            dt = start + timedelta(days=d)
            for h in range(24):
                x = HOURLY[h]*DOW[dt.weekday()]
                if c == "PHONE" and not 7 <= h < 19: x *= .1
                w.append(x)
        slots[c] = list(itertools.accumulate(w))
    for i in range(N - spike_tix):
        c = rng.choices(ch_ids, ch_w)[0]; s = rng.choices(range(len(slots[c])), cum_weights=slots[c])[0]
        out.append(dict(t=start + timedelta(hours=s, seconds=rng.randrange(3600)), channel=c, spike=None))
    for j in range(spike_tix):
        sp = spikes[j % len(spikes)]
        out.append(dict(t=start + timedelta(days=sp["day"], hours=sp["hour"], seconds=rng.randrange(7200)), channel=rng.choices(ch_ids, ch_w)[0], spike=sp))
    out.sort(key=lambda x: x["t"]); return out

def make_text(rng, intent, spike):
    if rng.random() < .04: s, b = rng.choice(VAGUE_TEMPLATES)
    else: s, b = rng.choice(INTENTS[intent]["templates"])
    ref = rng.randint(10000, 99999); s, b = s.format(ref=ref), b.format(ref=ref)
    r = rng.random()
    if spike and spike["incident"] and intent != "PRODUCT_SAFETY": b += " This is an outage affecting everyone here."
    elif r < .06: b += " This is urgent, please reply asap."
    elif r < .07: b += " I will contact my lawyer otherwise."
    return s, b

def generate_data(cfg, seed, db_path):
    rng = random.Random(seed); start = datetime.strptime(cfg["start_date"], "%Y-%m-%d"); end = start + timedelta(days=cfg["days"])
    conn = db.connect(db_path)
    db.init_schema(conn); db.seed_reference(conn); conn.commit()
    rules = RuleSet.from_db(conn); sla = rules.sla
    agents = build_agents(rng, cfg["agents"], start)
    states = {a["agent_id"]: agent_state(a) for a in agents}; alist = list(states.values())
    ints = list(INTENTS); iw = [INTENTS[i]["weight"] for i in ints]
    lang_ids = [l[0] for l in LANGUAGES]; lw = [l[2] for l in LANGUAGES]
    custs = []
    for k in range(cfg["customers"]):
        l = rng.choices(lang_ids, lw)[0]; nm = f"{rng.choice(FIRST)} {rng.choice(LAST)}"
        custs.append(dict(customer_id=f"CUS-{k+1:06d}", name=nm, email=f"cust{k+1}@example.test", phone=f"+1555{rng.randint(1000000, 9999999)}",
                          language=l, tier=rng.choices(["STANDARD", "GOLD", "PLATINUM"], [.8, .15, .05])[0], created=fmt(start - timedelta(days=rng.randint(30, 700)))))
    arrivals = make_arrivals(rng, cfg, start)
    T = {}; rows = dict(hist=[], asn=[], sla=[], res=[])
    asn_open = {}      # ticket -> assignment row (open)
    heap, cnt, waiting = [], itertools.count(), []
    tick = {"p": False}
    def push(t, kind, p): heapq.heappush(heap, (t, next(cnt), kind, p))
    def hist(t, to, now, actor="SYSTEM", aid=None, why=None, reason=None):
        why = why or reason
        assert_transition(t["status"], to) if t["status"] else None
        t["hseq"] += 1; rows["hist"].append(dict(ticket_id=t["id"], seq=t["hseq"], frm=t["status"], to=to, at=fmt(now), actor=actor, aid=aid, why=why)); t["status"] = to
    def slaev(t, typ, target, now, due=None, det=None):
        t["sseq"] += 1
        sid = f"SLA-{t['id']}" if t["sseq"] == 1 else f"SLA-{t['id']}-{t['sseq']:02d}"
        rows["sla"].append(dict(id=sid, ticket_id=t["id"], seq=t["sseq"], typ=typ, target=target, cal=t["channel"], due=fmt(due) if due else None,
                                at=fmt(now), wm=sla.targets(t["channel"], t["priority"])[0 if target == "RESPONSE" else 1], det=det))
    def asn(t, typ, frm, to, now, reason, score=None, dec=None):
        t["aseq"] += 1
        r = dict(id=f"ASN-{t['id']}-{t['aseq']:03d}", ticket_id=t["id"], seq=t["aseq"], typ=typ, frm=frm, to=to, queue=t["queue"], at=fmt(now), rel=None, reason=reason, score=score, dec=dec)
        rows["asn"].append(r); return r
    def enter_wait(t, now):
        waiting.append(t); t["wait_token"] += 1; t["unlogged"] = True
        push(sla.escalation_due(t["channel"], t["priority"], now), "ESC", (t, t["wait_token"]))
        if not tick["p"]: tick["p"] = True; push(now + timedelta(minutes=5), "TICK", None)
    def escalate(t, now, why):
        hist(t, "ESCALATED", now, reason=why); t["escalated"] = 1
        asn(t, "ESCALATE", t["agent"], None, now, why); slaev(t, "ESCALATION", "RESPONSE", now, None, why)
    def dur(t):
        base = {"PHONE": 12, "CHAT": 25, "EMAIL": 70}[t["channel"]]*{"CRITICAL": 2, "HIGH": 1.3}.get(t["priority"], 1)*(1.5 if t["intent"] == "TECH_FAULT" else 1)
        return max(5, rng.lognormvariate(math.log(base), .5)*(.6 if t["cycle"] > 1 else 1))
    fail_cache, ver = {}, [0]
    def attempt(t, now):
        excl = frozenset(t["visited"]) if t["xfer_from"] else frozenset()
        ck = (t["lang"], tuple(t["skills"]), excl); hr = int(now.timestamp()//3600)
        if fail_cache.get(ck) == (ver[0], hr) and not t["unlogged"]: return False
        d = route(dict(language=t["lang"], required_skills=t["skills"]), alist, now, exclude=excl, prefer=t["prefer"])
        dj = json.dumps(dict(priority=t["priority"], required_skills=t["skills"], language=t["lang"], considered=d.considered, rejections=d.rejection_counts, top=d.candidates), separators=(",", ":"))
        if d.agent_id is None:
            fail_cache[ck] = (ver[0], hr)
            if t["unlogged"]:
                asn(t, "UNASSIGNED", t["agent"], None, now, d.reason_code, None, dj); t["unlogged"] = False
                if t["status"] in ("IN_PROGRESS", "ASSIGNED"): hist(t, "OPEN", now, reason="requeued: " + d.reason_code)
            return False
        a = states[d.agent_id]; a.active += 1
        typ = "TRANSFER" if t["xfer_from"] else ("REASSIGN" if t["cycle"] > 1 else "ASSIGN")
        r = asn(t, typ, t["xfer_from"], a.agent_id, now, ("TRANSFER:" + t["xfer_why"]) if t["xfer_from"] else d.reason_code, d.score, dj)
        asn_open[t["id"]] = r; t["agent"] = a.agent_id
        if t["xfer_from"]: t["transfers"] += 1
        t["visited"].add(a.agent_id)
        t["xfer_from"] = None; t["unlogged"] = False
        hist(t, "ASSIGNED", now, "SYSTEM", None, "routed to " + a.agent_id)
        dl = {"PHONE": (0, 90), "CHAT": (30, 240), "EMAIL": (120, 5400)}[t["channel"]]
        push(now + timedelta(seconds=rng.randint(*dl)*(.2 if t["priority"] == "CRITICAL" else 1)), "START", (t, t["cycle"]))
        return True
    def release(t, now):
        r = asn_open.pop(t["id"]); r["rel"] = fmt(now); states[t["agent"]].active -= 1; ver[0] += 1
    def try_all(now):
        waiting.sort(key=lambda t: (-t["escalated"], -PRIORITIES.index(t["priority"]), t["created"]))
        for t in list(waiting):
            if attempt(t, now): waiting.remove(t)
    ticket_no = 0
    for ar in arrivals: push(ar["t"], "ARRIVE", ar)
    while heap and heap[0][0] <= end:
        now, _, kind, p = heapq.heappop(heap)
        if kind == "ARRIVE":
            ticket_no += 1; c = rng.choice(custs); spike = p["spike"]
            if spike: intent = rng.choice(["TECH_FAULT", "TECH_FAULT", "PRODUCT_SAFETY", "LOGIN_ISSUE"]) if spike["incident"] else rng.choice(["BILLING_DISPUTE", "PAYMENT_FAILED", "REFUND_REQUEST"])
            else: intent = rng.choices(ints, iw)[0]
            subj, body = make_text(rng, intent, spike)
            ci = rules.classify_intent(subj + " " + body); prio, applied, safety = rules.priority(ci, subj + " " + body, c["tier"])
            ch = p["channel"]; t0 = now + timedelta(seconds=2)
            rd, sd = sla.deadlines(ch, prio, now)
            t = dict(id=tid(ticket_no), cust=c["customer_id"], channel=ch, intent=ci, lang=c["language"], queue=rules.queue_for(ci, safety), priority=prio, status=None,
                     agent=None, subject=subj, body=body, created=now, resp_due=rd, resol_due=sd, first_resp=None, resolved=None, closed=None, reopens=0, transfers=0,
                     escalated=0, safety=int(safety), skills=rules.required_skills(ci, safety), hseq=0, sseq=0, aseq=0, cycle=1, visited=set(), prefer=set(), xfer_from=None, xfer_why=None,
                     wait_token=0, unlogged=True, pauses=[], paused_at=None, resp_logged=False, res_logged=False, last_res_agent=None, resolutions=[], customer_msgs=[], agent_times=[], plan=None, tier=c["tier"])
            T[t["id"]] = t
            hist(t, "NEW", now, "CUSTOMER", c["customer_id"], "ticket created")
            slaev(t, "START", "RESPONSE", now, rd); slaev(t, "START", "RESOLUTION", now, sd)
            push(rd, "SLACHK", (t, "RESPONSE", rd)); push(sd, "SLACHK", (t, "RESOLUTION", sd))
            hist(t, "OPEN", t0, reason=f"intent={ci} priority={prio}")
            enter_wait(t, t0)
            if attempt(t, t0): waiting.remove(t)
        elif kind == "TICK":
            tick["p"] = False; try_all(now)
            if waiting: tick["p"] = True; push(now + timedelta(minutes=5), "TICK", None)
        elif kind == "ESC":
            t, tok = p
            if t in waiting and t["wait_token"] == tok and t["status"] in ("OPEN", "REOPENED"): escalate(t, now, "WAIT_THRESHOLD_EXCEEDED")
        elif kind == "SLACHK":
            t, tgt, due = p
            if tgt == "RESPONSE":
                if t["first_resp"] is None and not t["resp_logged"]: slaev(t, "BREACH", tgt, due, due); t["resp_logged"] = True
            elif not t["res_logged"] and not t["paused_at"] and due == t["resol_due"] and not t["resolutions"]:
                slaev(t, "BREACH", tgt, due, due); t["res_logged"] = True
        elif kind == "START":
            t, cyc = p
            if t["cycle"] != cyc or t["status"] != "ASSIGNED": continue
            hist(t, "IN_PROGRESS", now, "AGENT", t["agent"], "agent started work"); t["agent_times"].append((now, t["agent"]))
            if t["first_resp"] is None:
                t["first_resp"] = now
                if not t["resp_logged"]: slaev(t, "MET", "RESPONSE", now, t["resp_due"]); t["resp_logged"] = True
            d = dur(t); x = rng.random()
            n_x = t["transfers"]
            if (n_x == 0 and x < .10) or (n_x == 1 and x < .25):
                t["xfer_why"] = rng.choice(["SKILL_GAP", "LANGUAGE_NEEDED", "WORKLOAD_REBALANCE", "WRONG_QUEUE"])
                push(now + timedelta(minutes=.45*d), "END", (t, cyc, "TRANSFER"))
            else:
                w = 0
                if t["channel"] != "PHONE" and rng.random() < .3:
                    w = rng.uniform(30, 480); push(now + timedelta(minutes=.5*d), "PEND", (t, cyc, w))
                push(now + timedelta(minutes=d + w), "END", (t, cyc, "RESOLVE"))
        elif kind == "PEND":
            t, cyc, w = p
            if t["cycle"] != cyc: continue
            hist(t, "PENDING_CUSTOMER", now, "AGENT", t["agent"], "waiting for customer"); t["paused_at"] = now
            
            if t["cycle"] == 1: slaev(t, "PAUSE", "RESOLUTION", now)
            push(now + timedelta(minutes=w), "RESUME", (t, cyc))
        elif kind == "RESUME":
            t, cyc = p
            hist(t, "IN_PROGRESS", now, "CUSTOMER", t["cust"], "customer replied"); t["customer_msgs"].append(now)
            t["pauses"].append((t["paused_at"], now)); t["paused_at"] = None
            if t["cycle"] == 1: slaev(t, "RESUME", "RESOLUTION", now)
            if t["cycle"] == 1 and not t["resolutions"]:
                _, nd = sla.deadlines(t["channel"], t["priority"], t["created"], t["pauses"])
                t["resol_due"] = nd; slaev(t, "DUE_ADJUSTED", "RESOLUTION", now, nd); push(nd, "SLACHK", (t, "RESOLUTION", nd))
        elif kind == "END":
            t, cyc, what = p
            if t["cycle"] != cyc: continue
            ag = t["agent"]
            if what == "TRANSFER":
                release(t, now); t["agent"] = None; t["xfer_from"] = ag; t["visited"].add(ag)
                if t["transfers"] + 1 >= 2: escalate(t, now, "TRANSFER_LIMIT")
                t["wait_token"] += 1; t["unlogged"] = True
                if attempt(t, now): pass
                else: enter_wait(t, now)
            else:
                hist(t, "RESOLVED", now, "AGENT", ag, "resolved"); release(t, now)
                n = len(t["resolutions"]) + 1; t["resolved"] = now; t["last_res_agent"] = ag; t["agent"] = None; t["prefer"] = {ag}
                if not t["res_logged"] and n == 1:
                    slaev(t, "MET", "RESOLUTION", now, t["resol_due"]); t["res_logged"] = True
                b = (t["first_resp"] and t["first_resp"] > t["resp_due"]) or now > t["resol_due"]
                score = max(1, min(5, round(rng.gauss(4.3 - (1.3 if b else 0) - .6*t["transfers"], .8)))) if rng.random() < .55 else None
                t["resolutions"].append(dict(n=n, at=now, agent=ag, code=rng.choice(["FIXED", "INFO_PROVIDED", "REFUNDED", "WORKAROUND", "NO_ACTION_NEEDED"]),
                                             csat=score, csat_at=fmt(now + timedelta(minutes=rng.randint(5, 600))) if score else None))
                if rng.random() < .06 and n < 3: push(now + timedelta(hours=rng.uniform(1, 48)), "REOPEN", (t, n))
                push(now + timedelta(hours=72), "CLOSE", (t, n))
        elif kind == "REOPEN":
            t, n = p
            if t["status"] != "RESOLVED" or len(t["resolutions"]) != n: continue
            hist(t, "REOPENED", now, "CUSTOMER", t["cust"], "customer reopened"); t["customer_msgs"].append(now)
            t["reopens"] += 1; t["cycle"] += 1; t["resolved"] = t["resolutions"][-1]["at"]; t["xfer_from"] = None
            t["wait_token"] += 1; t["unlogged"] = True
            if not attempt(t, now): enter_wait(t, now)
        elif kind == "CLOSE":
            t, n = p
            if t["status"] == "RESOLVED" and len(t["resolutions"]) == n: hist(t, "CLOSED", now, reason="auto-close after 72h"); t["closed"] = now
    return conn, rules, agents, custs, T, rows, end

def build_messages(rng, cfg, T, end):
    target = cfg["messages"]; out = {}
    for t in T.values():
        m = [(t["created"], "C", None)]
        if t["first_resp"]: m.append((t["first_resp"], "A", t["agent_times"][0][1]))
        m += [(x, "C", None) for x in t["customer_msgs"]]
        out[t["id"]] = m
    total = sum(len(v) for v in out.values())
    if total > target: raise RuntimeError(f"mandatory messages {total} exceed target {target}")
    elig = [t for t in T.values() if t["first_resp"]]
    for _ in range(target - total):
        t = rng.choice(elig); hi = t["closed"] or t["resolved"] or end; hi = max(hi, t["first_resp"])
        lo = t["first_resp"]; ts = lo + (hi - lo)*rng.random()
        ag = [a for tt, a in t["agent_times"] if tt <= ts] or [t["agent_times"][0][1]]
        out[t["id"]].append((ts.replace(microsecond=0), rng.choice("CA"), ag[-1]))
    return out

def persist(conn, cfg, seed, mode, rules, agents, custs, T, rows, msgs, end):
    conn.executemany("INSERT INTO agent VALUES (?,?,?,?,?,?)", [(a["agent_id"], a["name"], a["max_concurrent"], "ACTIVE", a["pattern"], a["hired"]) for a in agents])
    conn.executemany("INSERT INTO agent_skill VALUES (?,?,?)", [(a["agent_id"], s, p) for a in agents for s, p in a["skills"].items()])
    conn.executemany("INSERT INTO agent_language VALUES (?,?,?)", [(a["agent_id"], l, int(i == 0)) for a in agents for i, l in enumerate(a["langs"])])
    conn.executemany("INSERT INTO agent_shift (agent_id,weekday,start_min_utc,end_min_utc,effective_from) VALUES (?,?,?,?,?)",
                     [(a["agent_id"], d, s, e, "2026-01-01") for a in agents for d, s, e in a["shifts"]])
    conn.executemany("INSERT INTO customer VALUES (?,?,?,?,?,?,?)", [(c["customer_id"], c["name"], c["email"], c["phone"], c["language"], c["tier"], c["created"]) for c in custs])
    live = ("ASSIGNED", "IN_PROGRESS", "PENDING_CUSTOMER")
    tk = []
    for t in T.values():
        tk.append((t["id"], t["cust"], t["channel"], t["intent"], t["lang"], t["queue"], t["priority"], t["status"], t["agent"] if t["status"] in live else None, t["subject"],
                   fmt(t["created"]), fmt(t["first_resp"]), fmt(t["resolutions"][-1]["at"]) if t["resolutions"] else None, fmt(t["closed"]),
                   fmt(t["resp_due"]), fmt(t["resol_due"]), t["reopens"], t["transfers"], t["escalated"], t["safety"]))
    conn.executemany("INSERT INTO ticket VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", tk)
    conn.executemany("INSERT INTO ticket_status_history VALUES (?,?,?,?,?,?,?,?)", [(h["ticket_id"], h["seq"], h["frm"], h["to"], h["at"], h["actor"], h["aid"], h["why"]) for h in rows["hist"]])
    conn.executemany("INSERT INTO assignment_event VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", [(r["id"], r["ticket_id"], r["seq"], r["typ"], r["frm"], r["to"], r["queue"], r["at"], r["rel"], r["reason"], r["score"], r["dec"]) for r in rows["asn"]])
    conn.executemany("INSERT INTO sla_event VALUES (?,?,?,?,?,?,?,?,?,?)", [(r["id"], r["ticket_id"], r["seq"], r["typ"], r["target"], r["cal"], r["due"], r["at"], r["wm"], r["det"]) for r in rows["sla"]])
    res = []
    for t in T.values():
        for r in t["resolutions"]:
            res.append((f"RES-{t['id']}-{r['n']:02d}", t["id"], r["n"], fmt(r["at"]), r["agent"], r["code"], "Resolved by agent", r["csat"], r["csat_at"]))
    conn.executemany("INSERT INTO resolution VALUES (?,?,?,?,?,?,?,?,?)", res)
    mrows = []
    for tid_, m in msgs.items():
        m.sort(key=lambda x: (x[0], x[1] != "C"))
        t = T[tid_]
        for i, (ts, who, ag) in enumerate(m, 1):
            body = t["body"] if i == 1 else ("Thanks for contacting us, we are looking into this." if who == "A" else "Thank you, here is the extra detail you asked for.")
            mrows.append((f"MSG-{tid_}-{i:03d}", tid_, i, "INBOUND" if who == "C" else "OUTBOUND", "CUSTOMER" if who == "C" else "AGENT", ag if who == "A" else None, body, fmt(ts)))
    conn.executemany("INSERT INTO message VALUES (?,?,?,?,?,?,?,?)", mrows)
    conn.executemany("INSERT INTO dataset_meta VALUES (?,?)", [("as_of_utc", fmt(end)), ("seed", str(seed)), ("mode", mode), ("start_utc", cfg["start_date"] + "T00:00:00Z")])
    conn.commit()
