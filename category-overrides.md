# Category Overrides

Use these addenda together with `project-completion.md`. Only apply the section that matches the target project.

## Analytics and Reporting

Projects:

- `project_1_1_loan_delinquency`
- `project_1_2_employee_turnover`
- `project_1_3_cdt_rates`

### Extra Task - Automated Executive Report

Create or improve `src/report_generator.py` so it can be run as:

```bash
python src/report_generator.py --output reports/
```

The report should generate HTML and/or PDF outputs with:

- Statistical summary of key findings
- Up to 4 business-relevant charts
- Table of top insights with severity
- Actionable recommendations
- Run date, author, and basic analysis metadata

Style constraints:

- Use a professional financial palette
- Preferred brand colors: `#1E3A5F` and `#F4A500`

## Data Infrastructure

Projects:

- `project_2_1_audit_db`
- `project_2_2_fraud_detection`
- `project_2_3_fin_dwh`

### Extra Task - Container and Data Quality Hardening

If containerization is relevant to the current implementation, add or improve:

- `docker-compose.yml`
- `Dockerfile`
- `scripts/init_db.sh`
- `src/data_quality.py`

Important:

- Inspect the current backend first. If the project is currently SQLite-based, do not blindly convert it to PostgreSQL unless explicitly requested.
- If you add data-quality checks, include:
  - null percentage
  - duplicate detection
  - referential integrity checks where applicable
  - numeric range validation
- If the project remains local-first, containerization may wrap the current database choice rather than force a migration.

## Automation

Projects:

- `project_3_1_audit_automation`
- `project_3_2_financial_model`
- `project_3_3_kpi_dashboard`

### Extra Task - Professional CLI And Externalized Config

Refactor or extend the project so it exposes a clear CLI and validated config:

- Use Click for new CLI work
- Add descriptive `--help`
- Use progress bars only where there is real long-running work
- Use `rich` for readable terminal output where it adds value
- Support `--dry-run` when a command performs side effects
- Add `config/settings.yaml`
- Load and validate config before execution
- Remove hardcoded paths and operational values where practical

## Python Development and Parsing

Projects:

- `project_4_1_sfc_scraper`
- `project_4_2_audit_cli`
- `project_4_3_xbrl_parser`

### Extra Guidance

- Do not force framework changes when the current interface is already appropriate
- Preserve `argparse` for `project_4_2_audit_cli` unless the request explicitly asks for a CLI redesign
- Prefer reliability, testability, and path safety over adding new architecture

## BI and Analytics

Projects:

- `project_5_tableau_prep`
- `project_6_ibm_analyst`
- `project_7_yale_finance`
- `project_8_financial_modeling`
- `project_9_google_bi`

### Extra Guidance

- Keep SQL-first projects SQL-first
- Add helper Python only when needed for validation, reproducibility, or local execution
- Favor business-readable outputs, charts, and explanation over unnecessary backend complexity

## ML and Generative AI

Projects:

- `project_10_generative_ai`
- `project_2_2_fraud_detection` when the task is model-centric

### Extra Task - Experiment Tracking, Model Card, And Inference Surface

Add or improve:

- MLflow tracking for experiments or scoring runs
- `MODEL_CARD.md`
- An inference interface appropriate to the project

For classic prediction projects, prefer:

- `POST /predict`
- `POST /batch`
- `GET /health`
- `GET /model-info`

For retrieval or generative projects, adapt the interface to the actual workflow, but expose:

- a health endpoint
- a metadata/model-info endpoint
- a primary inference endpoint

Avoid conflicting instructions:

- `project_2_2_fraud_detection` should keep infrastructure and ML concerns aligned rather than treated as two unrelated implementations.
