from config.reference_data import TRANSITIONS
class InvalidTransition(ValueError): pass
def can_transition(a, b): return b in TRANSITIONS.get(a, [])
def assert_transition(a, b):
    if not can_transition(a, b): raise InvalidTransition(f"{a} -> {b} is not allowed")
