# Batch README Prompt

Use this prompt when the goal is to refresh README files across multiple Project Supernova projects quickly.

---

I have multiple projects inside the Project Supernova repository that already contain baseline scaffolding. For each project listed below, rewrite only the `README.md` so another developer can understand and run the project quickly.

## General Rules

- Write in English.
- Keep each README under 150 lines.
- Base the README on the actual current files and entrypoints, not assumed filenames.
- Do not invent services, notebooks, APIs, or folders that do not exist.
- If a project has known limitations or partial implementations, state them clearly.

## Output Format For Each README

```md
# [Project Name]
> [One sentence: what it does and why it matters]

## Stack
[technology badges or compact stack list]

## Quick Start
```bash
# 5 commands or fewer when realistic
```

## What It Does
[2-3 short paragraphs]

## File Structure
```text
[commented tree based on actual files]
```

## Configuration
[env vars, config files, or CLI flags actually used]

## Known Limitations
[short honest list]
```

## Required Working Method

For each listed project:

1. Inspect the current `src/`, `tests/`, and top-level files.
2. Identify the real run command.
3. Use the existing project name and domain language.
4. Keep the README practical and execution-oriented.

## Suggested Project List Format

### Project: `project_1_2_employee_turnover`
- Relevant files: `src/...`
- Stack: `...`

### Project: `project_1_3_cdt_rates`
- Relevant files: `src/...`
- Stack: `...`

Repeat for each project in scope.
