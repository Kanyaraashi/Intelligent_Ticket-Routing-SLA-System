# Validation & KPI Report
_Generated 2026-11-03 19:48 UTC from the actual SQLite databases._

## Dataset: starter

### KPIs
| KPI | Value |
|---|---|
| total_tickets | 500 |
| resolved_tickets | 450 |
| open_tickets | 50 |
| unassigned_tickets | 42 |
| avg_first_response_min | 288.1 |
| avg_resolution_min | 529.07 |
| escalations | 129 |
| reopened_tickets | 26 |
| transfers | 47 |
| avg_csat | 3.99 |
| csat_responses | 260 |
| capacity_violations | 1 |
| reopening_rate_pct | 5.2 |
| response_breaches | 97 |
| resolution_breaches | 20 |
| sla_breaches | 105 |
| sla_compliance_pct | 79.0 |
| routing_success_rate_pct | 95.2 |
| avg_queue_wait_min | 269.76 |
| skill_mismatches | 0 |
| language_mismatches | 0 |
| avg_agent_utilization_pct | 31.55 |
| as_of_utc | 2026-07-08T00:00:00Z |

### Validation checks
| Check | Issues | Status |
|---|---|---|
| PRIMARY_KEY_UNIQUENESS | 0 | PASS |
| FOREIGN_KEY_INTEGRITY | 0 | PASS |
| ALLOWED_VALUES | 0 | PASS |
| REQUIRED_FIELDS | 0 | PASS |
| DUPLICATE_RECORDS | 0 | PASS |
| DATE_ORDERING | 0 | PASS |
| LIFECYCLE_TRANSITIONS | 0 | PASS |
| ASSIGNMENT_HISTORY | 0 | PASS |
| AGENT_CAPACITY | 1 | ISSUES |
| SKILLS_AND_LANGUAGES | 0 | PASS |
| SLA_CALCULATIONS | 1 | ISSUES |
| ESCALATION_TIMING | 1 | ISSUES |
| MESSAGE_THREADS | 0 | PASS |
| REOPEN_HISTORY | 1 | ISSUES |
| DERIVED_VALUES | 0 | PASS |
| TRANSFER_LOOPS | 1 | ISSUES |
| PRIORITY_RULES | 1 | ISSUES |

### Injected anomalies (detector vs ground truth)
| Anomaly | Type | Record | Detected |
|---|---|---|---|
| ANOM-001 | TRANSFER_LOOP | TKT-2026-000063 | YES |
| ANOM-002 | CAPACITY_EXCEEDED | ASN-TKT-2026-000335-001 | YES |
| ANOM-003 | SLA_IGNORES_CALENDAR | TKT-2026-000001 | YES |
| ANOM-004 | REOPEN_HISTORY_LOST | TKT-2026-000020 | YES |
| ANOM-005 | SAFETY_PRIORITY_VIOLATION | TKT-2026-000067 | YES |

Validation issues total: 6; attributable to injected anomalies (incl. knock-on effects): 6; **accidental integrity failures: 0**

## Dataset: full

### KPIs
| KPI | Value |
|---|---|
| total_tickets | 30000 |
| resolved_tickets | 29756 |
| open_tickets | 244 |
| unassigned_tickets | 221 |
| avg_first_response_min | 178.06 |
| avg_resolution_min | 426.19 |
| escalations | 5477 |
| reopened_tickets | 1781 |
| transfers | 3723 |
| avg_csat | 3.98 |
| csat_responses | 17135 |
| capacity_violations | 3 |
| reopening_rate_pct | 5.94 |
| response_breaches | 4262 |
| resolution_breaches | 887 |
| sla_breaches | 4388 |
| sla_compliance_pct | 85.37 |
| routing_success_rate_pct | 99.89 |
| avg_queue_wait_min | 156.81 |
| skill_mismatches | 0 |
| language_mismatches | 0 |
| avg_agent_utilization_pct | 35.67 |
| as_of_utc | 2026-09-29T00:00:00Z |

### Validation checks
| Check | Issues | Status |
|---|---|---|
| PRIMARY_KEY_UNIQUENESS | 0 | PASS |
| FOREIGN_KEY_INTEGRITY | 0 | PASS |
| ALLOWED_VALUES | 0 | PASS |
| REQUIRED_FIELDS | 0 | PASS |
| DUPLICATE_RECORDS | 0 | PASS |
| DATE_ORDERING | 0 | PASS |
| LIFECYCLE_TRANSITIONS | 0 | PASS |
| ASSIGNMENT_HISTORY | 0 | PASS |
| AGENT_CAPACITY | 1 | ISSUES |
| SKILLS_AND_LANGUAGES | 0 | PASS |
| SLA_CALCULATIONS | 1 | ISSUES |
| ESCALATION_TIMING | 0 | PASS |
| MESSAGE_THREADS | 0 | PASS |
| REOPEN_HISTORY | 1 | ISSUES |
| DERIVED_VALUES | 0 | PASS |
| TRANSFER_LOOPS | 1 | ISSUES |
| PRIORITY_RULES | 1 | ISSUES |

### Injected anomalies (detector vs ground truth)
| Anomaly | Type | Record | Detected |
|---|---|---|---|
| ANOM-001 | TRANSFER_LOOP | TKT-2026-000105 | YES |
| ANOM-002 | CAPACITY_EXCEEDED | ASN-TKT-2026-022712-002 | YES |
| ANOM-003 | SLA_IGNORES_CALENDAR | TKT-2026-000001 | YES |
| ANOM-004 | REOPEN_HISTORY_LOST | TKT-2026-000031 | YES |
| ANOM-005 | SAFETY_PRIORITY_VIOLATION | TKT-2026-000041 | YES |

Validation issues total: 5; attributable to injected anomalies (incl. knock-on effects): 5; **accidental integrity failures: 0**

