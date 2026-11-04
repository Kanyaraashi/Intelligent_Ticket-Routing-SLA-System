# Limitations
- **No DB-level service layer.** Lifecycle operations (assign, transfer, escalate, resolve, reopen) are implemented inside the simulation and validated in the data; there is no interactive "create ticket / transfer ticket" write API or UI. The dashboard simulation is read-only by design.
- Keyword intent classifier works on English text only (customer language affects routing, not text).
- Calendars are expressed in UTC (no per-region time zones / DST).
- Agents are only checked for shift at assignment time; a ticket may continue after the shift ends.
- Resolution SLA applies to the first resolution cycle only; reopened cycles are not given new SLA deadlines.
- Anomaly #1 (capacity) is injected by lowering one agent's `max_concurrent` to one below its observed peak; anomaly #5 also recomputes SLA dates for the wrong priority, so its escalation-timing check also fires (a knock-on effect, not an accident).
- Synthetic data: queues show long waits for rare language/skill combinations at night; ~220 tickets are still waiting at the end of the 90-day window.
- Generated data are synthetic; message bodies are template text.
- GitHub publication and screenshots must be done by you (see START_HERE.md).
