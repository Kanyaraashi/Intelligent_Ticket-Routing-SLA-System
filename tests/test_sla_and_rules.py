from datetime import datetime, timedelta
from src.sla import BusinessCalendar, add_working_minutes, working_minutes_between
from config.reference_data import PRIORITIES
import pytest
from src.lifecycle import can_transition, assert_transition, InvalidTransition

EMAIL = BusinessCalendar([0,1,2,3,4], 480, 1080)           # Mon-Fri 08:00-18:00 UTC
def test_deadline_inside_hours():
    assert add_working_minutes(EMAIL, datetime(2026,7,1,9,0), 60) == datetime(2026,7,1,10,0)   # Wed
def test_after_hours_starts_next_open():
    assert add_working_minutes(EMAIL, datetime(2026,7,1,22,0), 60) == datetime(2026,7,2,9,0)
def test_weekend_skipped_friday_evening():
    assert add_working_minutes(EMAIL, datetime(2026,7,3,17,30), 60) == datetime(2026,7,6,8,30)  # Fri 17:30 +60 -> Mon 08:30
def test_holiday_skipped():
    cal = BusinessCalendar([0,1,2,3,4], 480, 1080, {datetime(2026,7,6).date()})
    assert add_working_minutes(cal, datetime(2026,7,3,17,30), 60) == datetime(2026,7,7,8,30)
def test_pause_extends_deadline():
    due = add_working_minutes(EMAIL, datetime(2026,7,1,9,0), 120, pauses=[(datetime(2026,7,1,9,30), datetime(2026,7,1,10,30))])
    assert due == datetime(2026,7,1,12,0)
def test_working_minutes_between_roundtrip():
    s = datetime(2026,7,3,16,0); d = add_working_minutes(EMAIL, s, 300)
    assert abs(working_minutes_between(EMAIL, s, d) - 300) < 1e-6
def test_not_wall_clock(rules):
    s = datetime(2026,7,3,17,0)  # Friday evening email, LOW (480 working min)
    r, _ = rules.sla.deadlines("EMAIL", "LOW", s)
    assert r > s + timedelta(minutes=480) + timedelta(hours=24)
def test_critical_uses_24x7(rules):
    s = datetime(2026,7,4,3,0)   # Saturday night
    r, _ = rules.sla.deadlines("EMAIL", "CRITICAL", s)
    assert r == s + timedelta(minutes=15)
def test_escalation_due_half_target(rules):
    s = datetime(2026,7,1,9,0); assert rules.sla.escalation_due("EMAIL", "HIGH", s) == s + timedelta(minutes=30)

def test_lifecycle_valid_and_invalid():
    assert can_transition("NEW", "OPEN") and can_transition("RESOLVED", "REOPENED") and can_transition("CLOSED", "REOPENED")
    for a, b in [("NEW","RESOLVED"),("CLOSED","ASSIGNED"),("OPEN","RESOLVED"),("RESOLVED","IN_PROGRESS")]:
        with pytest.raises(InvalidTransition): assert_transition(a, b)

def test_priority_safety_rule_cannot_be_lowered(rules):
    p, applied, safe = rules.priority("GENERAL_QUERY", "my charger is overheating", "STANDARD")
    assert (p, safe) == ("CRITICAL", True)
def test_priority_urgent_and_tier(rules):
    assert rules.priority("PASSWORD_RESET", "please reset my password asap", "STANDARD")[0] == "HIGH"
    assert rules.priority("PASSWORD_RESET", "reset my password", "PLATINUM")[0] == "MEDIUM"
def test_intent_classification(rules):
    assert rules.classify_intent("I was charged twice on my invoice") == "BILLING_DISPUTE"
    assert rules.classify_intent("hello") == "GENERAL_QUERY"
def test_safety_requires_two_skills(rules):
    assert set(rules.required_skills("TECH_FAULT", True)) == {"TECHNICAL", "SAFETY"}
    assert rules.queue_for("TECH_FAULT", True) == "Q-SAFETY"
