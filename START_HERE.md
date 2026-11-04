# START HERE (beginner guide)
Do the steps in order. After each step, check "You should see". If not, read "If it fails".

## STEP 1 - Where to download the ZIP
Download `intelligent-ticket-routing-sla-system.zip` from the place the assistant gave you (chat attachment/download link). It goes to your **Downloads** folder.
You should see: the file in `C:\Users\<you>\Downloads`. If missing: download again from the chat.

## STEP 2 - Extract the ZIP
1. Open File Explorer -> Downloads. 2. **Right-click** the ZIP -> **Extract All...** 3. Choose `C:\projects` (create the folder if needed) -> **Extract**.
You should see: `C:\projects\intelligent-ticket-routing-sla-system\` containing `START_HERE.md`, `app.py`, `INSTALL.bat`.
If it fails: do not run files from inside the ZIP window; always extract first. Avoid very long paths.

## STEP 3 - Open the folder in VS Code
Install VS Code from https://code.visualstudio.com if needed. Open VS Code -> **File -> Open Folder...** -> pick `intelligent-ticket-routing-sla-system` (the folder that directly contains `app.py`) -> **Select Folder** -> click **Yes, I trust the authors**.
Open a terminal: **Terminal -> New Terminal** (PowerShell is fine).

## STEP 4 - Check Python
Type: `python --version`
You should see: `Python 3.11.x` or `3.12.x`.
If it fails ("not recognized"): install Python from https://www.python.org/downloads/ - **tick "Add python.exe to PATH"** - close and reopen VS Code and retry.

## STEP 5 - Install dependencies
Double-click `INSTALL.bat` in File Explorer (or run `.\INSTALL.bat` in the terminal).
You should see: `[OK] Installation finished.` A folder `.venv` appears.
If it fails: check internet; run INSTALL.bat again; if "execution policy" appears in PowerShell use `cmd /c INSTALL.bat`.

## STEP 6 - Starter dataset
A ready starter database is already in `data\starter.db`. To regenerate it, double-click `GENERATE_STARTER_DATA.bat`.
You should see: row counts (500 tickets, 20 agents, 2,000 messages). Takes ~5 seconds.

## STEP 7 - Launch the dashboard
Double-click `RUN_DASHBOARD.bat`. It stops older copies of this project's dashboard and starts the updated app on port 8501. Keep that window open.

## STEP 8 - Browser URL
Open **http://localhost:8501**. (If Windows Firewall asks, click Allow.) You should see "Executive Overview" with KPI cards.
If the page does not load: make sure the black window is still open and shows "You can now view your Streamlit app".

## STEP 9 - Test ticket routing
Left sidebar -> **Intelligent Routing**. Keep the defaults (subject "Charger overheating") -> click **Route this ticket**.
You should see: intent PRODUCT_SAFETY, priority CRITICAL, queue Q-SAFETY, a selected agent, a ranked table with score parts, and a table of rejected agents with reasons (OFF_SHIFT, MISSING_SKILL, LANGUAGE_MISMATCH, AT_CAPACITY). Change language to `hi` or the time to 03:00 and route again to see "no agent available" behaviour. Nothing is saved (read-only).

## STEP 10 - Inspect SLA calculations
Sidebar -> **SLA Monitoring**. Type a ticket id such as `TKT-2026-000010` and read its due dates and SLA events (START, PAUSE, RESUME, DUE_ADJUSTED, MET/BREACH). Deadlines skip nights, weekends and holidays (see Business calendars table).

## STEP 11 - Inspect anomalies
Sidebar -> **Anomaly Detection**. You should see 5 injected problems detected (capacity exceeded, SLA ignoring calendar, reopen history lost, transfer loop, safety priority violation) and an evaluation table showing "detected = True".

## STEP 12 - Run automated tests
Double-click `RUN_TESTS.bat`. You should see `42 passed`. If something fails, copy the red text and ask for help.

## STEP 13 - Generate the full dataset
Double-click `GENERATE_FULL_DATA.bat` (2-5 minutes). A full database is already included as `data\full.db`; the dashboard sidebar "Dataset" lets you switch. You should see 30,000 tickets, 100 agents, 100,000 messages.

## STEP 14 - Verify the validation report
Double-click `VALIDATE_DATA.bat` (starter) or run `.venv\Scripts\python scripts\validate_data.py --mode full`. Then `CREATE_REPORT.bat` writes `docs\VALIDATION_REPORT.md`. Expected: only the 5 injected anomalies appear; "ACCIDENTAL: 0".

## STEP 15 - Create a GitHub account (if needed)
Go to https://github.com -> **Sign up** -> enter email, password, username -> verify email.

## STEP 16 - Create a public repository
Click **+** (top right) -> **New repository** -> name `intelligent-ticket-routing-sla-system` -> choose **Public** -> do NOT tick "Add a README" -> **Create repository**.

## STEP 17 - Upload and push
Install Git from https://git-scm.com/download/win. In the VS Code terminal (inside the project folder):
```
git init
git add .
git commit -m "Initial commit: ticket routing and SLA system"
git branch -M main
git remote add origin https://github.com/<YOUR-USERNAME>/intelligent-ticket-routing-sla-system.git
git push -u origin main
```
A browser sign-in window may open - sign in. `.gitignore` already excludes `.venv` and caches. The large `data\full.db` and `exports\full` can be removed before pushing if GitHub complains about file size (>100 MB blocks push): delete them, they can be regenerated with GENERATE_FULL_DATA.bat.
Suggested commits: 1 schema+config, 2 generator, 3 routing+SLA, 4 validation+anomalies, 5 dashboard, 6 tests, 7 docs.

## STEP 18 - Verify the public repository
Open `https://github.com/<YOUR-USERNAME>/intelligent-ticket-routing-sla-system` in a **private/incognito window**. You must see the files without logging in.

## STEP 19 - Final submission link
Submit that URL, plus the ZIP if asked. Before submitting: fill in your own contribution in `docs\AI_USAGE.md`, and add 2-3 screenshots to `screenshots\`.
