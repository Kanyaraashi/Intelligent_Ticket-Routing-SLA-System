# AI Usage Disclosure
- **Claude (Anthropic)** generated the initial source code, SQL schema, tests, batch files and documentation in a single agentic session, and executed the project (install, generate, validate, test, dashboard smoke tests, zip) in a Linux sandbox.
 - GitHub Copilot AI, operating through the VS Code Copilot SDK, subsequently assisted with dashboard improvements and project documentation.
- AI accelerated: architecture, simulation logic, SLA calendar engine, validator, dashboard, docs.
- Verified by execution (real outputs): pytest results, validation reports, reproducibility checks, dashboard page rendering. The Windows `.bat` files were **not** executed (the sandbox is Linux) - they must be tested on your PC.
## Dashboard enhancement and personal contribution record

### My project requirements and review
- I requested clearer information about how the project works and how it addresses modern support operations problems.
- I asked for a more attractive Streamlit user interface while preserving the existing dashboard functionality.
- I identified that the "About the Project" section needed to explain the complete workflow in a way that evaluators and non-technical users could understand.
- I reported that the page styling caused text to be low contrast or nearly invisible, especially in content blocks.
- I reported port errors when restarting or double-clicking `RUN_DASHBOARD.bat` while another Streamlit instance was already running.

### How the dashboard code was changed
- Added a consistent visual theme to `app.py` using a light application background, dark blue sidebar, white metric cards, teal accents and softer borders and shadows.
- Added a gradient hero banner to the "About the Project" page.
- Organized the project explanation into three tabs:
  - **How the Project Works** for the operational workflow.
  - **Modern Problem It Solves** for the customer-support challenges addressed.
  - **Project Impact** for customer, operations and organizational benefits.
- Added five visible workflow stages covering ticket intake, classification, agent selection, SLA/lifecycle handling and outcome intelligence.
- Added styled information cards for problems and benefits.
- Added explanatory dashboard section documentation covering all dashboard pages and their purposes.

### UI bugs raised and fixes applied
- **Low-contrast "About the Project" text:** dark text colors were added to workflow cards, impact cards and Markdown headings, so content remains visible on the light card backgrounds.
- **Same-colored text and card background:** explicit foreground colors were added for card text, headings, list items and step-card labels.
- **Incomplete card visibility:** borders, white backgrounds and shadows were preserved so content blocks remain visually separated.
- **Stale Streamlit instance:** the earlier dashboard process was stopped and the updated application was started again on port 8501.
- **Port 8501 launcher error:** `RUN_DASHBOARD.bat` now stops older copies of this project's Streamlit process before starting the current `app.py`.
- **Browser launch:** the launcher opens the fixed address `http://localhost:8501` and always starts the current dashboard version on port 8501.

### Streamlit UI management
- Used Streamlit page layout, sidebar navigation, tabs, columns, metrics, dataframes, Plotly charts and custom HTML/CSS.
- Kept page behavior and database reads unchanged while adding presentation styles.
- Used the existing read-only database connection and routing simulation rather than creating a second data or routing implementation.
- Used CSS scoped to the application layout, sidebar, cards, Markdown content and primary buttons to keep the visual hierarchy consistent.
- Preserved responsive Streamlit containers so the dashboard still works at different window widths.

### Testing and verification
- Compiled `app.py` with Python to check syntax.
- Ran the project's headless Streamlit smoke test for the starter and full datasets.
- All dashboard pages passed for both datasets, including "About the Project."
- Verified the updated dashboard is available at `http://localhost:8501`.
- Verified that the updated launcher replaces older dashboard copies before starting port 8501.
- The dashboard is opened at `http://localhost:8501`; refreshing with `Ctrl+F5` loads the latest interface after browser caching.

### Personal responsibility
- [x] I reviewed the project requirements and dashboard behavior.
- [x] I reviewed and understood the purpose of the "About the Project" content and requested clearer business and workflow explanations.
- [x] I ran or requested verification of the updated Streamlit dashboard.
- [x] I reported visible UI problems, including low text contrast, poorly visible cards and stale port behavior.
- [x] I requested changes to `app.py`, `RUN_DASHBOARD.bat`, `START_HERE.md` and this AI usage documentation.
- [ ] I ran `INSTALL.bat` and documented its installation output.
- [ ] I ran `RUN_TESTS.bat` and documented the complete test result personally.
- [ ] I independently made additional source-code changes outside the AI-assisted changes listed above.
- I reviewed the dashboard output and requested corrections based on visible UI issues.
- I provided the project-workflow and business-context requirements for the final project narrative.
- I verified the launcher behavior when an existing Streamlit server was already running.
- No external LLM/API is used at runtime. No secrets are in the project.
