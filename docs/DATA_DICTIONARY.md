# Data Dictionary
Generated from `database/schema.sql` by `scripts/build_data_dictionary.py`. All timestamps are UTC text `YYYY-MM-DDTHH:MM:SSZ`.

## language

| Column | Type | Key | Required | Allowed values / rule | Description |
|---|---|---|---|---|---|
| language_code | TEXT | PK | yes |  |  |
| name | TEXT |  | yes |  |  |

## channel

| Column | Type | Key | Required | Allowed values / rule | Description |
|---|---|---|---|---|---|
| channel_id | TEXT | PK | yes | EMAIL,CHAT,PHONE |  |
| name | TEXT |  | yes |  |  |
| work_days | TEXT |  | yes |  | Comma list of weekdays, Monday=0 |
| open_min_utc | INTEGER |  | yes |  | Opening minute of day (UTC) |
| close_min_utc | INTEGER |  | yes |  | Closing minute of day (UTC) |

## skill

| Column | Type | Key | Required | Allowed values / rule | Description |
|---|---|---|---|---|---|
| skill_id | TEXT | PK | yes |  |  |
| name | TEXT |  | yes |  |  |

## queue

| Column | Type | Key | Required | Allowed values / rule | Description |
|---|---|---|---|---|---|
| queue_id | TEXT | PK | yes |  |  |
| name | TEXT |  | yes |  |  |
| primary_skill_id | TEXT | FK->skill | yes |  |  |
| is_active | INTEGER |  | yes |  |  |

## intent

| Column | Type | Key | Required | Allowed values / rule | Description |
|---|---|---|---|---|---|
| intent_id | TEXT | PK | yes |  |  |
| name | TEXT |  | yes |  |  |
| keywords | TEXT |  | yes |  | JSON list of classifier keywords |
| default_priority | TEXT |  | yes | LOW,MEDIUM,HIGH,CRITICAL |  |
| default_queue_id | TEXT | FK->queue | yes |  |  |
| is_safety | INTEGER |  | yes |  |  |

## intent_skill

| Column | Type | Key | Required | Allowed values / rule | Description |
|---|---|---|---|---|---|
| intent_id | TEXT | PK FK->intent | yes |  |  |
| skill_id | TEXT | PK FK->skill | yes |  |  |

## priority_rule

| Column | Type | Key | Required | Allowed values / rule | Description |
|---|---|---|---|---|---|
| rule_id | TEXT | PK | yes |  |  |
| rule_type | TEXT |  | yes | KEYWORD,TIER_BUMP |  |
| match_value | TEXT |  | yes |  |  |
| priority | TEXT |  | yes | LOW,MEDIUM,HIGH,CRITICAL | Business priority; safety rules force CRITICAL |
| is_safety | INTEGER |  | yes |  |  |
| effective_from | TEXT |  | yes |  | Start of validity |
| effective_to | TEXT |  | no |  | End of validity (NULL = open-ended) |

## sla_policy

| Column | Type | Key | Required | Allowed values / rule | Description |
|---|---|---|---|---|---|
| policy_id | TEXT | PK | yes |  |  |
| priority | TEXT |  | yes | LOW,MEDIUM,HIGH,CRITICAL | Business priority; safety rules force CRITICAL |
| channel_id | TEXT | FK->channel | yes |  |  |
| response_target_min | INTEGER |  | yes |  | Target in WORKING minutes |
| resolution_target_min | INTEGER |  | yes |  | Target in WORKING minutes |
| use_24x7 | INTEGER |  | yes |  | 1 = critical priority uses 24x7 calendar |
| effective_from | TEXT |  | yes |  | Start of validity |
| effective_to | TEXT |  | no |  | End of validity (NULL = open-ended) |

## holiday

| Column | Type | Key | Required | Allowed values / rule | Description |
|---|---|---|---|---|---|
| holiday_id | TEXT | PK | yes |  |  |
| holiday_date | TEXT |  | yes |  |  |
| channel_id | TEXT | FK->channel | no |  |  |
| name | TEXT |  | yes |  |  |

## agent

| Column | Type | Key | Required | Allowed values / rule | Description |
|---|---|---|---|---|---|
| agent_id | TEXT | PK | yes |  | AGT-NNNNNN |
| name | TEXT |  | yes |  |  |
| max_concurrent | INTEGER |  | yes | max_concurrent BETWEEN 1 AND 20 | Maximum simultaneous tickets (hard capacity limit) |
| status | TEXT |  | yes | ACTIVE,INACTIVE | Lifecycle state |
| shift_pattern | TEXT |  | yes |  |  |
| hired_date | TEXT |  | yes |  |  |

## agent_skill

| Column | Type | Key | Required | Allowed values / rule | Description |
|---|---|---|---|---|---|
| agent_id | TEXT | PK FK->agent | yes |  | AGT-NNNNNN |
| skill_id | TEXT | PK FK->skill | yes |  |  |
| proficiency | INTEGER |  | yes | proficiency BETWEEN 1 AND 5 | 1 (basic) to 5 (expert) |

## agent_language

| Column | Type | Key | Required | Allowed values / rule | Description |
|---|---|---|---|---|---|
| agent_id | TEXT | PK FK->agent | yes |  | AGT-NNNNNN |
| language_code | TEXT | PK FK->language | yes |  |  |
| is_primary | INTEGER |  | yes |  |  |

## agent_shift

| Column | Type | Key | Required | Allowed values / rule | Description |
|---|---|---|---|---|---|
| shift_id | INTEGER | PK | yes |  |  |
| agent_id | TEXT | FK->agent | yes |  | AGT-NNNNNN |
| weekday | INTEGER |  | yes | weekday BETWEEN 0 AND 6 |  |
| start_min_utc | INTEGER |  | yes |  |  |
| end_min_utc | INTEGER |  | yes |  |  |
| effective_from | TEXT |  | yes |  | Start of validity |
| effective_to | TEXT |  | no |  | End of validity (NULL = open-ended) |

## customer

| Column | Type | Key | Required | Allowed values / rule | Description |
|---|---|---|---|---|---|
| customer_id | TEXT | PK | yes |  | CUS-NNNNNN |
| name | TEXT |  | yes |  |  |
| email | TEXT |  | yes |  |  |
| phone | TEXT |  | no |  |  |
| language_code | TEXT | FK->language | yes |  |  |
| tier | TEXT |  | yes | STANDARD,GOLD,PLATINUM |  |
| created_at_utc | TEXT |  | yes |  | UTC creation time |

## ticket

| Column | Type | Key | Required | Allowed values / rule | Description |
|---|---|---|---|---|---|
| ticket_id | TEXT | PK | yes |  | Business key TKT-2026-NNNNNN |
| customer_id | TEXT | FK->customer | yes |  | CUS-NNNNNN |
| channel_id | TEXT | FK->channel | yes |  |  |
| intent_id | TEXT | FK->intent | yes |  |  |
| language_code | TEXT | FK->language | yes |  |  |
| queue_id | TEXT | FK->queue | yes |  |  |
| priority | TEXT |  | yes | LOW,MEDIUM,HIGH,CRITICAL | Business priority; safety rules force CRITICAL |
| status | TEXT |  | yes | NEW,OPEN,ASSIGNED,IN_PROGRESS,PENDING_CUSTOMER,RESOLVED,CLOSED,REOPENED,ESCALATED | Lifecycle state |
| current_agent_id | TEXT | FK->agent | no |  | Agent currently responsible (NULL when waiting/resolved/closed) |
| subject | TEXT |  | yes |  |  |
| created_at_utc | TEXT |  | yes |  | UTC creation time |
| first_response_at_utc | TEXT |  | no |  | Time of first agent message (derived) |
| resolved_at_utc | TEXT |  | no |  | Latest resolution time (derived from resolution) |
| closed_at_utc | TEXT |  | no |  |  |
| sla_response_due_utc | TEXT |  | yes |  | Calendar-aware response deadline |
| sla_resolution_due_utc | TEXT |  | yes |  | Calendar-aware resolution deadline (extended by SLA pauses) |
| reopen_count | INTEGER |  | yes |  | Number of REOPENED transitions (derived) |
| transfer_count | INTEGER |  | yes |  | Number of TRANSFER assignment events (derived) |
| is_escalated | INTEGER |  | yes |  | 1 if ever escalated |
| safety_flag | INTEGER |  | yes |  | 1 if safety rule matched at routing time |

## ticket_status_history

| Column | Type | Key | Required | Allowed values / rule | Description |
|---|---|---|---|---|---|
| ticket_id | TEXT | PK FK->ticket | yes |  | Business key TKT-2026-NNNNNN |
| seq | INTEGER | PK | yes |  |  |
| from_status | TEXT |  | no |  |  |
| to_status | TEXT |  | yes |  |  |
| changed_at_utc | TEXT |  | yes |  |  |
| actor_type | TEXT |  | yes | SYSTEM,AGENT,CUSTOMER |  |
| actor_id | TEXT |  | no |  |  |
| reason | TEXT |  | no |  |  |

## message

| Column | Type | Key | Required | Allowed values / rule | Description |
|---|---|---|---|---|---|
| message_id | TEXT | PK | yes |  | MSG-<ticket_id>-NNN |
| ticket_id | TEXT | FK->ticket | yes |  | Business key TKT-2026-NNNNNN |
| seq | INTEGER |  | yes |  |  |
| direction | TEXT |  | yes | INBOUND,OUTBOUND |  |
| sender_type | TEXT |  | yes | CUSTOMER,AGENT |  |
| sender_agent_id | TEXT | FK->agent | no |  |  |
| body | TEXT |  | yes |  |  |
| sent_at_utc | TEXT |  | yes |  |  |

## assignment_event

| Column | Type | Key | Required | Allowed values / rule | Description |
|---|---|---|---|---|---|
| assignment_id | TEXT | PK | yes |  | ASN-<ticket_id>-NNN |
| ticket_id | TEXT | FK->ticket | yes |  | Business key TKT-2026-NNNNNN |
| seq | INTEGER |  | yes |  |  |
| event_type | TEXT |  | yes | ASSIGN,TRANSFER,REASSIGN,ESCALATE,UNASSIGNED |  |
| from_agent_id | TEXT | FK->agent | no |  |  |
| to_agent_id | TEXT | FK->agent | no |  |  |
| queue_id | TEXT | FK->queue | yes |  |  |
| event_at_utc | TEXT |  | yes |  |  |
| released_at_utc | TEXT |  | no |  | When the agent stopped holding the ticket (NULL = still open) |
| reason_code | TEXT |  | yes |  | Why the event happened (e.g. ROUTED_BEST_SCORE, NO_AGENT_ON_SHIFT, WAIT_THRESHOLD_EXCEEDED, TRANSFER:SKILL_GAP) |
| score | REAL |  | no |  | Routing score 0-100 |
| decision_json | TEXT |  | no |  | Explainable routing decision: rejections, top candidates and score parts |

## sla_event

| Column | Type | Key | Required | Allowed values / rule | Description |
|---|---|---|---|---|---|
| sla_event_id | TEXT | PK | yes |  | SLA-<ticket_id> (first event) then SLA-<ticket_id>-NN |
| ticket_id | TEXT | FK->ticket | yes |  | Business key TKT-2026-NNNNNN |
| seq | INTEGER |  | yes |  |  |
| event_type | TEXT |  | yes | START,PAUSE,RESUME,DUE_ADJUSTED,MET,BREACH,ESCALATION |  |
| target_type | TEXT |  | yes | RESPONSE,RESOLUTION |  |
| calendar_channel_id | TEXT | FK->channel | no |  |  |
| due_at_utc | TEXT |  | no |  |  |
| occurred_at_utc | TEXT |  | yes |  |  |
| working_minutes_target | INTEGER |  | no |  |  |
| details | TEXT |  | no |  |  |

## resolution

| Column | Type | Key | Required | Allowed values / rule | Description |
|---|---|---|---|---|---|
| resolution_id | TEXT | PK | yes |  | RES-<ticket_id>-CC (CC = resolution cycle) |
| ticket_id | TEXT | FK->ticket | yes |  | Business key TKT-2026-NNNNNN |
| cycle_no | INTEGER |  | yes |  |  |
| resolved_at_utc | TEXT |  | yes |  | Latest resolution time (derived from resolution) |
| resolved_by_agent_id | TEXT | FK->agent | yes |  |  |
| resolution_code | TEXT |  | yes |  |  |
| summary | TEXT |  | no |  |  |
| csat_score | INTEGER |  | no | csat_score BETWEEN 1 AND 5 | Customer satisfaction 1-5 (optional survey) |
| csat_submitted_at_utc | TEXT |  | no |  |  |

## dataset_meta

| Column | Type | Key | Required | Allowed values / rule | Description |
|---|---|---|---|---|---|
| key | TEXT | PK | yes |  |  |
| value | TEXT |  | yes |  |  |
