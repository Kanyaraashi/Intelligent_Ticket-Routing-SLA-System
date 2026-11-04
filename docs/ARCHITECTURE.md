# Architecture
```
config/ (reference data, modes.json)  ->  database/schema.sql
src/rules.py        intent classification, priority + safety rules, queue + skill selection (loaded from DB)
src/sla.py          business calendars, working-time deadlines, pauses, escalation due
src/routing.py      pure function route(): hard constraints, score, explanation
src/lifecycle.py    legal state transitions
src/generator.py    deterministic data + event-driven simulation (uses rules/sla/routing/lifecycle)
src/anomalies.py    5 anomaly injectors (write ground truth) + rule-based detector (never reads it)
src/validation.py   17 check families         src/metrics.py  KPIs from SQL
src/simulation.py   READ-ONLY what-if routing (dashboard)
src/build.py        generate -> persist -> inject -> export CSV/JSON -> manifest
app.py              Streamlit dashboard (9 pages, read-only DB connection)
scripts/            CLI entry points used by the .bat files
```
Design choices: one shared pure routing function used by the generator and the dashboard simulation (same behaviour everywhere); SQLite for zero-install; rules as data; ground truth only written by the injector and read only by evaluation code (a test asserts application code never references it).
Exception handling: no agent -> UNASSIGNED event + queue retry + escalation; illegal transition -> exception; generator fails fast if mandatory messages exceed the target.
