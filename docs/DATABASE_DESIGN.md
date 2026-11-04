# Database Design
SQLite, foreign keys ON, UTC text timestamps. See `ER_DIAGRAM.md` (Mermaid) and `DATA_DICTIONARY.md` (every field).

**13 core entities:** Customer, Channel, Ticket, Message, Intent, Language, PriorityRule, Agent, Skill, Queue, AssignmentEvent, SLAEvent, Resolution.
**Bridge / supporting tables:** `intent_skill` (Intent N:M Skill), `agent_skill` (Agent N:M Skill + proficiency), `agent_language` (Agent N:M Language + primary flag), `agent_shift` (weekly UTC shifts with effective dates), `sla_policy` (priority x channel targets, effective-dated), `holiday`, `ticket_status_history` (lifecycle audit trail), `dataset_meta` (as-of time, seed, mode).

## Why it is designed this way
- **History is append-only.** Assignments, SLA events, status changes and resolutions are separate event tables. A reopen adds a new `resolution` cycle and new assignment events; nothing is overwritten.
- **Ticket stores only current state and derived summaries** (`status`, `current_agent_id`, `reopen_count`, `transfer_count`, due dates). Every derived value is re-checked by the validator against the event tables.
- **Hard rules live in data, not code:** intents, keywords, priority rules, SLA targets, calendars and holidays are rows (`RuleSet.from_db`), so business users can change them without touching Python.
- **Integrity:** primary keys everywhere, foreign keys on every relationship, CHECK constraints for all enums and ranges, indexes on ticket status/created, and on ticket/agent keys of event tables.
- **Transactions:** the generator persists everything in one transaction batch per table group and commits once; injected anomalies are applied in one transaction.
- **Cardinalities:** Customer 1:N Ticket; Ticket 1:N Message / AssignmentEvent / SLAEvent / Resolution / status history; Agent N:M Skill and Language; Intent N:M Skill; Queue 1:N Ticket; Channel 1:N Ticket.
- **Unassigned tickets** are represented by `current_agent_id IS NULL` plus an `UNASSIGNED` assignment event whose `reason_code` and `decision_json` explain why.
