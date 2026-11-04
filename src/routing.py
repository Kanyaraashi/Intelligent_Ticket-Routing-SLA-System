"""Deterministic, explainable routing. Hard constraints first (never violated), then a transparent 0-100 score."""
from dataclasses import dataclass, field

W_AVAIL, W_RUNWAY, W_PROF, W_PRIMARY_LANG, W_CONT = 40, 20, 20, 10, 10   # sums to 100

@dataclass
class AgentState:
    agent_id: str
    max_concurrent: int
    skills: dict            # skill_id -> proficiency 1-5
    languages: list         # first = primary
    shifts: dict            # weekday -> [(start_min, end_min)]
    active: int = 0
    status: str = "ACTIVE"

def shift_remaining(shifts, now):
    """Minutes left in the shift covering `now` (joins an overnight shift that continues after midnight); 0 = off shift."""
    wd, m = now.weekday(), now.hour*60 + now.minute
    for s, e in shifts.get(wd, ()):
        if s <= m < e:
            rem = e - m
            if e == 1440:
                for s2, e2 in shifts.get((wd+1) % 7, ()):
                    if s2 == 0: rem += e2
            return rem
    return 0

@dataclass
class Decision:
    agent_id: str = None
    score: float = None
    reason_code: str = "NO_ELIGIBLE_AGENT"
    candidates: list = field(default_factory=list)   # eligible agents ranked (explain) 
    rejected: list = field(default_factory=list)     # (agent_id, [reasons]) (explain=True only)
    rejection_counts: dict = field(default_factory=dict)
    considered: int = 0

def route(ticket, agents, now, exclude=(), prefer=(), explain=False):
    """ticket: dict(language, required_skills). Returns Decision. Mandatory: ACTIVE, on shift, all skills, language, spare capacity."""
    need, lang = ticket["required_skills"], ticket["language"]
    elig, rej, counts = [], [], {}
    qualified = on_shift = 0
    for a in agents:
        why = []
        if a.status != "ACTIVE": why.append("INACTIVE")
        missing = [s for s in need if s not in a.skills]
        if missing: why.append("MISSING_SKILL:" + "+".join(missing))
        if lang not in a.languages: why.append("LANGUAGE_MISMATCH")
        rem = shift_remaining(a.shifts, now)
        if rem <= 0: why.append("OFF_SHIFT")
        if a.active >= a.max_concurrent: why.append("AT_CAPACITY")
        if a.agent_id in exclude: why.append("EXCLUDED_PREVIOUS_HANDLER")
        if not missing and lang in a.languages and a.status == "ACTIVE":
            qualified += 1
            if rem > 0: on_shift += 1
        if why:
            for w in why: k = w.split(":")[0]; counts[k] = counts.get(k, 0) + 1
            if explain: rej.append((a.agent_id, why))
            continue
        parts = dict(availability=W_AVAIL*(1 - a.active/a.max_concurrent), shift_runway=W_RUNWAY*min(rem/240, 1),
                     proficiency=W_PROF*(sum(a.skills[s] for s in need)/len(need))/5,
                     language=W_PRIMARY_LANG if a.languages[0] == lang else W_PRIMARY_LANG/2,
                     continuity=W_CONT if a.agent_id in prefer else 0)
        elig.append((round(sum(parts.values()), 2), a.agent_id, {k: round(v, 2) for k, v in parts.items()}))
    elig.sort(key=lambda x: (-x[0], x[1]))
    d = Decision(considered=len(agents), rejection_counts=counts, rejected=rej,
                 candidates=[dict(agent_id=i, score=s, breakdown=p) for s, i, p in elig[: (len(elig) if explain else 5)]])
    if elig:
        d.agent_id, d.score, d.reason_code = elig[0][1], elig[0][0], "ROUTED_BEST_SCORE"
    elif qualified == 0: d.reason_code = "NO_QUALIFIED_AGENT"
    elif on_shift == 0: d.reason_code = "NO_AGENT_ON_SHIFT"
    else: d.reason_code = "ALL_QUALIFIED_AT_CAPACITY"
    return d
