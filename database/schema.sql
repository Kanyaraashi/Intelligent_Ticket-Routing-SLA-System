-- Intelligent Ticket Routing & SLA System: SQLite schema. All timestamps are UTC ISO-8601 text (YYYY-MM-DDTHH:MM:SSZ).
PRAGMA foreign_keys = ON;

-- ===== Reference entities =====
CREATE TABLE language (
  language_code TEXT PRIMARY KEY, name TEXT NOT NULL);
CREATE TABLE channel (
  channel_id TEXT PRIMARY KEY CHECK (channel_id IN ('EMAIL','CHAT','PHONE')),
  name TEXT NOT NULL, work_days TEXT NOT NULL,
  open_min_utc INTEGER NOT NULL, close_min_utc INTEGER NOT NULL);
CREATE TABLE skill (
  skill_id TEXT PRIMARY KEY, name TEXT NOT NULL);
CREATE TABLE queue (
  queue_id TEXT PRIMARY KEY, name TEXT NOT NULL,
  primary_skill_id TEXT NOT NULL REFERENCES skill(skill_id), is_active INTEGER NOT NULL DEFAULT 1);
CREATE TABLE intent (
  intent_id TEXT PRIMARY KEY, name TEXT NOT NULL, keywords TEXT NOT NULL,
  default_priority TEXT NOT NULL CHECK (default_priority IN ('LOW','MEDIUM','HIGH','CRITICAL')),
  default_queue_id TEXT NOT NULL REFERENCES queue(queue_id), is_safety INTEGER NOT NULL DEFAULT 0);
CREATE TABLE intent_skill (
  intent_id TEXT NOT NULL REFERENCES intent(intent_id), skill_id TEXT NOT NULL REFERENCES skill(skill_id),
  PRIMARY KEY (intent_id, skill_id));
CREATE TABLE priority_rule (
  rule_id TEXT PRIMARY KEY,
  rule_type TEXT NOT NULL CHECK (rule_type IN ('KEYWORD','TIER_BUMP')),
  match_value TEXT NOT NULL, priority TEXT NOT NULL CHECK (priority IN ('LOW','MEDIUM','HIGH','CRITICAL')),
  is_safety INTEGER NOT NULL DEFAULT 0, effective_from TEXT NOT NULL, effective_to TEXT);
CREATE TABLE sla_policy (
  policy_id TEXT PRIMARY KEY,
  priority TEXT NOT NULL CHECK (priority IN ('LOW','MEDIUM','HIGH','CRITICAL')),
  channel_id TEXT NOT NULL REFERENCES channel(channel_id),
  response_target_min INTEGER NOT NULL, resolution_target_min INTEGER NOT NULL,
  use_24x7 INTEGER NOT NULL DEFAULT 0, effective_from TEXT NOT NULL, effective_to TEXT,
  UNIQUE (priority, channel_id, effective_from));
CREATE TABLE holiday (
  holiday_id TEXT PRIMARY KEY, holiday_date TEXT NOT NULL, channel_id TEXT REFERENCES channel(channel_id),
  name TEXT NOT NULL);

-- ===== Agents =====
CREATE TABLE agent (
  agent_id TEXT PRIMARY KEY, name TEXT NOT NULL,
  max_concurrent INTEGER NOT NULL CHECK (max_concurrent BETWEEN 1 AND 20),
  status TEXT NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE','INACTIVE')),
  shift_pattern TEXT NOT NULL, hired_date TEXT NOT NULL);
CREATE TABLE agent_skill (
  agent_id TEXT NOT NULL REFERENCES agent(agent_id), skill_id TEXT NOT NULL REFERENCES skill(skill_id),
  proficiency INTEGER NOT NULL CHECK (proficiency BETWEEN 1 AND 5), PRIMARY KEY (agent_id, skill_id));
CREATE TABLE agent_language (
  agent_id TEXT NOT NULL REFERENCES agent(agent_id), language_code TEXT NOT NULL REFERENCES language(language_code),
  is_primary INTEGER NOT NULL DEFAULT 0, PRIMARY KEY (agent_id, language_code));
CREATE TABLE agent_shift (
  shift_id INTEGER PRIMARY KEY AUTOINCREMENT, agent_id TEXT NOT NULL REFERENCES agent(agent_id),
  weekday INTEGER NOT NULL CHECK (weekday BETWEEN 0 AND 6),
  start_min_utc INTEGER NOT NULL, end_min_utc INTEGER NOT NULL CHECK (end_min_utc <= 1440 AND end_min_utc > start_min_utc),
  effective_from TEXT NOT NULL, effective_to TEXT);

-- ===== Customers & tickets =====
CREATE TABLE customer (
  customer_id TEXT PRIMARY KEY, name TEXT NOT NULL, email TEXT NOT NULL, phone TEXT,
  language_code TEXT NOT NULL REFERENCES language(language_code),
  tier TEXT NOT NULL CHECK (tier IN ('STANDARD','GOLD','PLATINUM')), created_at_utc TEXT NOT NULL);
CREATE TABLE ticket (
  ticket_id TEXT PRIMARY KEY,
  customer_id TEXT NOT NULL REFERENCES customer(customer_id),
  channel_id TEXT NOT NULL REFERENCES channel(channel_id),
  intent_id TEXT NOT NULL REFERENCES intent(intent_id),
  language_code TEXT NOT NULL REFERENCES language(language_code),
  queue_id TEXT NOT NULL REFERENCES queue(queue_id),
  priority TEXT NOT NULL CHECK (priority IN ('LOW','MEDIUM','HIGH','CRITICAL')),
  status TEXT NOT NULL CHECK (status IN ('NEW','OPEN','ASSIGNED','IN_PROGRESS','PENDING_CUSTOMER','RESOLVED','CLOSED','REOPENED','ESCALATED')),
  current_agent_id TEXT REFERENCES agent(agent_id),
  subject TEXT NOT NULL,
  created_at_utc TEXT NOT NULL, first_response_at_utc TEXT, resolved_at_utc TEXT, closed_at_utc TEXT,
  sla_response_due_utc TEXT NOT NULL, sla_resolution_due_utc TEXT NOT NULL,
  reopen_count INTEGER NOT NULL DEFAULT 0, transfer_count INTEGER NOT NULL DEFAULT 0,
  is_escalated INTEGER NOT NULL DEFAULT 0, safety_flag INTEGER NOT NULL DEFAULT 0);
CREATE TABLE ticket_status_history (
  ticket_id TEXT NOT NULL REFERENCES ticket(ticket_id), seq INTEGER NOT NULL,
  from_status TEXT, to_status TEXT NOT NULL, changed_at_utc TEXT NOT NULL,
  actor_type TEXT NOT NULL CHECK (actor_type IN ('SYSTEM','AGENT','CUSTOMER')), actor_id TEXT, reason TEXT,
  PRIMARY KEY (ticket_id, seq));
CREATE TABLE message (
  message_id TEXT PRIMARY KEY, ticket_id TEXT NOT NULL REFERENCES ticket(ticket_id), seq INTEGER NOT NULL,
  direction TEXT NOT NULL CHECK (direction IN ('INBOUND','OUTBOUND')),
  sender_type TEXT NOT NULL CHECK (sender_type IN ('CUSTOMER','AGENT')),
  sender_agent_id TEXT REFERENCES agent(agent_id), body TEXT NOT NULL, sent_at_utc TEXT NOT NULL,
  UNIQUE (ticket_id, seq));
CREATE TABLE assignment_event (
  assignment_id TEXT PRIMARY KEY, ticket_id TEXT NOT NULL REFERENCES ticket(ticket_id), seq INTEGER NOT NULL,
  event_type TEXT NOT NULL CHECK (event_type IN ('ASSIGN','TRANSFER','REASSIGN','ESCALATE','UNASSIGNED')),
  from_agent_id TEXT REFERENCES agent(agent_id), to_agent_id TEXT REFERENCES agent(agent_id),
  queue_id TEXT NOT NULL REFERENCES queue(queue_id), event_at_utc TEXT NOT NULL, released_at_utc TEXT,
  reason_code TEXT NOT NULL, score REAL, decision_json TEXT, UNIQUE (ticket_id, seq));
CREATE TABLE sla_event (
  sla_event_id TEXT PRIMARY KEY, ticket_id TEXT NOT NULL REFERENCES ticket(ticket_id), seq INTEGER NOT NULL,
  event_type TEXT NOT NULL CHECK (event_type IN ('START','PAUSE','RESUME','DUE_ADJUSTED','MET','BREACH','ESCALATION')),
  target_type TEXT NOT NULL CHECK (target_type IN ('RESPONSE','RESOLUTION')),
  calendar_channel_id TEXT REFERENCES channel(channel_id),
  due_at_utc TEXT, occurred_at_utc TEXT NOT NULL, working_minutes_target INTEGER, details TEXT, UNIQUE (ticket_id, seq));
CREATE TABLE resolution (
  resolution_id TEXT PRIMARY KEY, ticket_id TEXT NOT NULL REFERENCES ticket(ticket_id), cycle_no INTEGER NOT NULL,
  resolved_at_utc TEXT NOT NULL, resolved_by_agent_id TEXT NOT NULL REFERENCES agent(agent_id),
  resolution_code TEXT NOT NULL, summary TEXT,
  csat_score INTEGER CHECK (csat_score BETWEEN 1 AND 5), csat_submitted_at_utc TEXT, UNIQUE (ticket_id, cycle_no));
CREATE TABLE dataset_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);

CREATE INDEX ix_ticket_status ON ticket(status);
CREATE INDEX ix_ticket_created ON ticket(created_at_utc);
CREATE INDEX ix_msg_ticket ON message(ticket_id);
CREATE INDEX ix_asn_ticket ON assignment_event(ticket_id);
CREATE INDEX ix_asn_agent ON assignment_event(to_agent_id);
CREATE INDEX ix_sla_ticket ON sla_event(ticket_id);
CREATE INDEX ix_res_ticket ON resolution(ticket_id);
