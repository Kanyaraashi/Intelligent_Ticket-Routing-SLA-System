from datetime import datetime
from src.routing import AgentState, route, shift_remaining
WED_10 = datetime(2026,7,1,10,0)
DAY = {d: [(540, 1020)] for d in range(7)}
def ag(i, skills=None, langs=None, shifts=DAY, active=0, mx=3):
    return AgentState(i, mx, skills or {"BILLING": 4}, langs or ["en"], shifts, active)
T = dict(language="en", required_skills=["BILLING"])
def test_best_score_prefers_lower_load():
    d = route(T, [ag("A", active=2), ag("B", active=0)], WED_10); assert d.agent_id == "B"
def test_skill_is_mandatory():
    d = route(T, [ag("A", skills={"TECHNICAL": 5})], WED_10); assert d.agent_id is None and d.reason_code == "NO_QUALIFIED_AGENT"
def test_all_skills_required():
    d = route(dict(language="en", required_skills=["SAFETY","TECHNICAL"]), [ag("A", skills={"SAFETY": 5})], WED_10); assert d.agent_id is None
def test_language_is_mandatory():
    d = route(dict(language="hi", required_skills=["BILLING"]), [ag("A"), ag("B", langs=["hi","en"])], WED_10); assert d.agent_id == "B"
def test_capacity_never_exceeded():
    d = route(T, [ag("A", active=3, mx=3)], WED_10); assert d.agent_id is None and d.reason_code == "ALL_QUALIFIED_AT_CAPACITY"
def test_shift_enforced():
    d = route(T, [ag("A")], datetime(2026,7,1,3,0)); assert d.agent_id is None and d.reason_code == "NO_AGENT_ON_SHIFT"
def test_overnight_shift_spans_midnight():
    night = {2: [(1260, 1440)], 3: [(0, 300)]}
    assert shift_remaining(night, datetime(2026,7,1,23,0)) == 60 + 300     # Wed 23:00 -> Thu 05:00
    assert shift_remaining(night, datetime(2026,7,2,2,0)) == 180
def test_no_agent_available_exception_reason_recorded():
    d = route(T, [], WED_10); assert d.agent_id is None and d.reason_code == "NO_QUALIFIED_AGENT"
def test_excluded_agents_prevent_transfer_loop():
    d = route(T, [ag("A"), ag("B", active=1)], WED_10, exclude={"A"}); assert d.agent_id == "B"
def test_deterministic_tiebreak():
    assert route(T, [ag("B"), ag("A")], WED_10).agent_id == "A"
def test_continuity_bonus():
    d = route(T, [ag("A"), ag("B", active=0)], WED_10, prefer={"B"}); assert d.agent_id == "B"
def test_explain_lists_rejections():
    d = route(T, [ag("A", skills={"TECHNICAL": 3}), ag("B")], WED_10, explain=True)
    assert dict(d.rejected)["A"] == ["MISSING_SKILL:BILLING"]
