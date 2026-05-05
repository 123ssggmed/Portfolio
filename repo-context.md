# Repo Context For Prompted Work

Use this file as the factual context block for any prompt in this pack.

## Repository Identity

- Workspace: `fintech-data-science-nexus` / Project Supernova
- Organization context: IRIS Compañía de Financiamiento
- Primary stack: Python, SQL, analytics, automation, BI, and generative AI
- Canonical project units: 18 top-level `project_*` directories

## Active Project Inventory

| Project | Short Name | Category |
|---|---|---|
| `project_1_1_loan_delinquency` | Loan Delinquency | Analytics and Reporting |
| `project_1_2_employee_turnover` | Employee Turnover | Analytics and Reporting |
| `project_1_3_cdt_rates` | CDT Rates | Analytics and Reporting |
| `project_2_1_audit_db` | Audit DB | Data Infrastructure |
| `project_2_2_fraud_detection` | Fraud Detection | Data Infrastructure + ML-adjacent |
| `project_2_3_fin_dwh` | Financial DWH | Data Infrastructure |
| `project_3_1_audit_automation` | Audit Automation | Automation |
| `project_3_2_financial_model` | Financial Model | Automation |
| `project_3_3_kpi_dashboard` | KPI Dashboard | Automation |
| `project_4_1_sfc_scraper` | SFC Scraper | Python Development and Parsing |
| `project_4_2_audit_cli` | Audit CLI | Python Development and Parsing |
| `project_4_3_xbrl_parser` | XBRL Parser | Python Development and Parsing |
| `project_5_tableau_prep` | Tableau Prep | BI and Analytics |
| `project_6_ibm_analyst` | IBM Analyst | BI and Analytics |
| `project_7_yale_finance` | Yale Finance | BI and Analytics |
| `project_8_financial_modeling` | Financial Modeling | BI and Analytics |
| `project_9_google_bi` | Google BI | BI and Analytics |
| `project_10_generative_ai` | Generative AI | ML and Generative AI |

## Baseline Deliverables Already Present

Assume every project already has:

- `README.md`
- `requirements.txt`
- `tests/`
- `setup.sh`
- `Makefile`
- `.gitignore`

Do not frame the repo as if most projects are missing those files unless you explicitly verify a regression.

## Standard Prompting Rules

- Inspect existing files before proposing work.
- Preserve user changes and existing generated artifacts unless removal is explicitly requested.
- Do not assume `src/main.py` is the entrypoint; use the current runnable script or CLI wrapper.
- Distinguish between baseline scaffolding work and higher-value hardening work.
- For infrastructure prompts, verify whether the project currently uses SQLite or another local backend before prescribing PostgreSQL-first changes.

## Repo Quirks

- The root contains legacy status reports and prompt drafts that may be outdated.
- Several root-level files named like `project_*.md` are not project directories.
- Some projects contain generated CSV, DB, PNG, or HTML artifacts in the project root or `src/`.
- `project_2_2_fraud_detection` overlaps infrastructure and ML concerns; prompt instructions should not conflict.

## Prompt Inputs To Fill Explicitly

When using prompts from this pack, always fill:

- Project name and directory
- Category
- Current objective
- Existing source files relevant to the task
- Desired output scope
- Constraints or acceptance criteria
