# Business Rules
## Classification and priority
1. **Intent** = keyword match on subject + first message (most keyword hits wins; no hit -> `GENERAL_QUERY`). Deterministic, no external AI.
2. **Priority** starts at the intent default, then keyword rules take the maximum, then a PLATINUM customer is bumped one level (capped at HIGH).
3. **Safety rule:** any safety keyword (overheating, smoke, caught fire, sparks, burn, electric shock, melted, exploded) forces **CRITICAL**, routes to `Q-SAFETY` and requires skills SAFETY **and** TECHNICAL. It can never be lowered.
## Routing (hard constraints, then score)
Agent must be ACTIVE, **on shift now**, have **all** required skills, **speak the ticket language**, have **spare capacity** (`active < max_concurrent`), and not be an excluded previous handler (on transfers).
Score (0-100): availability 40 x (1 - load/max) + shift runway 20 x min(minutes left/240, 1) + proficiency 20 x avg/5 + language 10 (primary) or 5 + continuity 10 (previous resolver on reopen). Ties -> lowest agent id.
No eligible agent -> ticket stays in its queue, an `UNASSIGNED` event records the reason (`NO_QUALIFIED_AGENT`, `NO_AGENT_ON_SHIFT`, `ALL_QUALIFIED_AT_CAPACITY`), the queue is retried every 5 simulated minutes, and waiting time is measured from creation to first assignment.
## SLA
- Targets are **working minutes** by priority x channel (`sla_policy`). Calendars (UTC): EMAIL Mon-Fri 08-18, CHAT Mon-Sat 06-22, PHONE Mon-Fri 07-19. Holidays (`holiday`) close a calendar (all channels or one). **CRITICAL uses a 24x7 calendar** (after-hours handling for safety incidents).
- Deadline = start + N *eligible* minutes (walks calendar segments; never `now + hours`). Tickets arriving after hours start counting at next opening.
- **Pause/resume:** `PENDING_CUSTOMER` pauses the resolution clock; on resume the due date is recomputed and a `DUE_ADJUSTED` event is stored. Response SLA is never paused.
- **Breach:** response breach if first response is after due (or none by as-of); resolution likewise for the first resolution cycle.
- **Escalation:** an unassigned ticket escalates after 50% of its response target in working minutes; a ticket on its 2nd transfer escalates immediately (`TRANSFER_LIMIT`).
## Lifecycle
NEW->OPEN->ASSIGNED->IN_PROGRESS->(PENDING_CUSTOMER)->RESOLVED->CLOSED (auto after 72h). RESOLVED/CLOSED->REOPENED->ASSIGNED. Escalation: OPEN/ASSIGNED/IN_PROGRESS/REOPENED->ESCALATED->ASSIGNED. Transfer: IN_PROGRESS->ASSIGNED (or ->OPEN if nobody free). Illegal transitions raise `InvalidTransition` and are re-checked by the validator.
Transfers exclude every agent who previously held the ticket, so loops cannot happen in valid data. Reopening keeps all earlier assignments and resolutions (new `cycle_no`).
