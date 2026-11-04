"""Business-calendar SLA engine. Deadlines = eligible WORKING time, never 'now + N hours'. All times naive UTC."""
import math
from datetime import datetime, timedelta, time, date

class BusinessCalendar:
    def __init__(self, days, open_min, close_min, holidays=frozenset()):
        self.days, self.open_min, self.close_min, self.holidays = frozenset(days), open_min, close_min, frozenset(holidays)
    def segments(self, start):
        d = start.date()
        for _ in range(4000):
            if d.weekday() in self.days and d not in self.holidays:
                base = datetime.combine(d, time.min)
                s, e = base + timedelta(minutes=self.open_min), base + timedelta(minutes=self.close_min)
                if e > start: yield max(s, start), e
            d += timedelta(days=1)
    def is_open(self, t):
        m = t.hour*60 + t.minute
        return t.weekday() in self.days and t.date() not in self.holidays and self.open_min <= m < self.close_min

def _subtract(s, e, pauses):
    cur = s
    for ps, pe in sorted(pauses):
        if pe <= cur or ps >= e: continue
        if ps > cur: yield cur, ps
        cur = max(cur, pe)
        if cur >= e: return
    if cur < e: yield cur, e

def add_working_minutes(cal, start, minutes, pauses=()):
    """Return the instant at which `minutes` of eligible (open, un-paused) time have elapsed since `start`."""
    remaining = float(minutes)
    for s, e in cal.segments(start):
        for a, b in _subtract(s, e, pauses):
            avail = (b - a).total_seconds()/60
            if avail >= remaining: return a + timedelta(minutes=remaining)
            remaining -= avail
    raise RuntimeError("calendar exhausted")

def working_minutes_between(cal, a, b, pauses=()):
    if b <= a: return 0.0
    tot = 0.0
    for s, e in cal.segments(a):
        if s >= b: break
        for x, y in _subtract(s, min(e, b), pauses):
            tot += (y - x).total_seconds()/60
    return tot

class SlaEngine:
    def __init__(self, channels, policy, holidays, esc_fraction=0.5):
        """channels: {id:(days,open,close)}; policy:{(prio,channel):(resp,resol,use24)}; holidays:[(date,channel|None)]"""
        self.policy, self.esc_fraction = policy, esc_fraction
        self.cal = {}
        for ch, (days, o, c) in channels.items():
            hs = {d for d, hc in holidays if hc in (None, ch)}
            self.cal[ch] = BusinessCalendar(days, o, c, hs)
        self.cal24 = BusinessCalendar(range(7), 0, 1440)
    def calendar(self, channel, priority):
        return self.cal24 if self.policy[(priority, channel)][2] else self.cal[channel]
    def targets(self, channel, priority): return self.policy[(priority, channel)][:2]
    def deadlines(self, channel, priority, start, pauses=()):
        cal = self.calendar(channel, priority); r, s = self.targets(channel, priority)
        return add_working_minutes(cal, start, r), add_working_minutes(cal, start, s, pauses)
    def escalation_due(self, channel, priority, since):
        r, _ = self.targets(channel, priority)
        return add_working_minutes(self.calendar(channel, priority), since, math.ceil(r*self.esc_fraction))
