"""RuleSet: intent classification, priority rules, queue selection, SLA engine; loadable from the database."""
import json
from datetime import datetime
from config.reference_data import PRIORITIES, ESCALATION_FRACTION
from .sla import SlaEngine

class RuleSet:
    def __init__(self, intents, rules, sla):
        self.intents, self.rules, self.sla = intents, rules, sla
        self.safety_keywords = [r["match"] for r in rules if r["is_safety"]]
    @classmethod
    def from_db(cls, conn):
        intents = {}
        for r in conn.execute("SELECT intent_id,name,keywords,default_priority,default_queue_id,is_safety FROM intent ORDER BY rowid"):
            intents[r[0]] = dict(name=r[1], keywords=json.loads(r[2]), priority=r[3], queue=r[4], safety=bool(r[5]), skills=[])
        for i, s in conn.execute("SELECT intent_id,skill_id FROM intent_skill ORDER BY rowid"): intents[i]["skills"].append(s)
        rules = [dict(id=a, type=b, match=c, priority=d, is_safety=bool(e)) for a, b, c, d, e in
                 conn.execute("SELECT rule_id,rule_type,match_value,priority,is_safety FROM priority_rule WHERE effective_to IS NULL ORDER BY rule_id")]
        channels = {r[0]: ([int(x) for x in r[1].split(",")], r[2], r[3]) for r in conn.execute("SELECT channel_id,work_days,open_min_utc,close_min_utc FROM channel")}
        policy = {(p, c): (a, b, bool(u)) for p, c, a, b, u in conn.execute("SELECT priority,channel_id,response_target_min,resolution_target_min,use_24x7 FROM sla_policy WHERE effective_to IS NULL")}
        hol = [(datetime.strptime(d, "%Y-%m-%d").date(), c) for d, c in conn.execute("SELECT holiday_date,channel_id FROM holiday")]
        return cls(intents, rules, SlaEngine(channels, policy, hol, ESCALATION_FRACTION))
    def classify_intent(self, text):
        t = text.lower(); best, score = "GENERAL_QUERY", 0
        for iid, i in self.intents.items():
            n = sum(1 for k in i["keywords"] if k in t)
            if n > score: best, score = iid, n
        return best
    def priority(self, intent_id, text, tier="STANDARD"):
        """-> (priority, applied_rule_ids, is_safety). Safety keywords force CRITICAL and can never be lowered."""
        t = text.lower(); p = PRIORITIES.index(self.intents[intent_id]["priority"]); applied, safety = [], self.intents[intent_id]["safety"]
        for r in self.rules:
            if r["type"] == "KEYWORD" and r["match"] in t:
                p = max(p, PRIORITIES.index(r["priority"])); applied.append(r["id"]); safety = safety or r["is_safety"]
        for r in self.rules:
            if r["type"] == "TIER_BUMP" and r["match"] == tier and p < PRIORITIES.index(r["priority"]):
                p = min(p + 1, PRIORITIES.index(r["priority"])); applied.append(r["id"])
        if safety: p = PRIORITIES.index("CRITICAL")
        return PRIORITIES[p], applied, safety
    def required_skills(self, intent_id, is_safety):
        s = list(self.intents[intent_id]["skills"])
        if is_safety:
            for x in ("SAFETY", "TECHNICAL"):
                if x not in s: s.append(x)
        return s
    def queue_for(self, intent_id, is_safety):
        return "Q-SAFETY" if is_safety else self.intents[intent_id]["queue"]
