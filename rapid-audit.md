# Rapid Audit Prompt

Use this prompt for a fast, structured diagnosis of a single project before deeper implementation work.

---

Analyze one project in the Project Supernova repository and return the result in exactly this format.

Important context:

- The project likely already has `README.md`, `requirements.txt`, `tests/`, `setup.sh`, `Makefile`, and `.gitignore`.
- Do not assume the gaps are missing baseline files. Inspect them and report their actual quality, completeness, and reliability.
- Use the current project directory as the source of truth, not the older root-level status reports.

## Prompt

PROJECT: `[name]`

## ESTADO ACTUAL
- Archivos encontrados: `[lista breve y relevante]`
- ¿Ejecutable sin modificaciones?: `[SÍ/NO + razón]`
- Dependencias detectadas: `[lista]`
- Bugs críticos encontrados: `[lista o "none"]`

## GAPS IDENTIFICADOS
- Documentación: `[quality gap, inconsistency, staleness, or "none"]`
- Tests: `[coverage or quality gap]`
- Calidad de código: `[logic, typing, logging, path, or error handling gap]`
- Infraestructura: `[runtime, packaging, config, data, or service gap]`

## PLAN DE ACCIÓN PRIORIZADO
| # | Tarea | Esfuerzo | Impacto | Semana |
|---|-------|----------|---------|--------|
| 1 | ... | Xh | Alto | 1 |

## SCORE DE MADUREZ
- Código: X/10
- Documentación: X/10
- Tests: X/10
- Usabilidad: X/10
- TOTAL: X/40

## Audit Rules

- Inspect actual files first.
- Prefer findings about correctness, maintainability, and usability over generic advice.
- If baseline files exist but are shallow or stale, call that out explicitly.
- If no critical bugs are found, say so plainly.
