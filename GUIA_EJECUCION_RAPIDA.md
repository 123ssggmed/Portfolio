# ⚡ GUÍA DE EJECUCIÓN RÁPIDA

Instrucciones paso a paso para ejecutar cada proyecto inmediatamente.

---

## 📋 TABLA DE CONTENIDOS

1. [Análisis & Reporting](#análisis--reporting)
2. [Infraestructura de Datos](#infraestructura-de-datos)
3. [Automatización](#automatización)
4. [Scraping & Parsing](#scraping--parsing)
5. [BI & Finanzas](#bi--finanzas)
6. [IA Generativa](#ia-generativa)

---

## 🔍 ANÁLISIS & REPORTING

### 1.1 Loan Delinquency Analysis

**Estado:** ✅ Listo para ejecutar

```bash
cd project_1_1_loan_delinquency

# Instalar dependencias
pip install pandas numpy matplotlib seaborn jupyter scikit-learn

# Generar datos
python src/generate_data.py

# Ejecutar análisis
python src/analysis.py

# (Opcional) Explorar con notebook
jupyter notebook notebooks/exploration.ipynb
```

**Outputs esperados:**
- `data/loans.csv` - Dataset generado
- Gráficos y estadísticas en consola
- `reports/` - Reportes generados

**Tiempo estimado:** 5-10 minutos

---

### 1.2 Employee Turnover Analysis

**Estado:** ⚠️ Necesita setup

```bash
cd project_1_2_employee_turnover

# Crear requirements.txt (temporal)
cat > requirements.txt << EOF
pandas>=1.3.0
numpy>=1.21.0
scikit-learn>=0.24.0
matplotlib>=3.4.0
seaborn>=0.11.0
EOF

pip install -r requirements.txt

# Ejecutar
python src/analysis.py
python src/prediction.py
```

**Próximas acciones:** Crear documentación detallada

**Tiempo estimado:** 3-5 minutos

---

### 1.3 CDT Rates Analysis

**Estado:** ⚠️ Necesita setup

```bash
cd project_1_3_cdt_rates

# Instalar dependencias
pip install pandas requests beautifulsoup4 numpy matplotlib

# Ejecutar en orden
python src/fetch_rates.py     # Obtiene datos
python src/analyze_trends.py  # Analiza tendencias
python src/forecast.py        # Predice tasas
```

**Datos procesados:**
- Tasas históricas CDT
- Análisis de tendencias
- Proyecciones futuras

**Tiempo estimado:** 5 minutos

---

## 🗄️ INFRAESTRUCTURA DE DATOS

### 2.1 Audit Requirements Database

**Estado:** ✅ Listo (requiere PostgreSQL)

```bash
cd project_2_1_audit_db

# Instalar dependencias
pip install psycopg2-binary sqlalchemy

# Prerequisito: PostgreSQL debe estar corriendo
# En macOS: brew install postgresql && brew services start postgresql
# En Linux: sudo apt install postgresql postgresql-contrib

# Crear base de datos
createdb audit_db

# Cargar schema
psql audit_db < sql/schema.sql

# Cargar datos de prueba
psql audit_db < sql/seed_data.sql

# Ejecutar pruebas
python src/test_queries.py

# Inicializar desde Python
python src/init_db.py
```

**Conexión desde Python:**
```python
from src.init_db import AuditDB
db = AuditDB(user="your_user", password="your_pass")
results = db.get_audit_requirements()
```

**Consultas disponibles:** Ver `sql/queries.sql`

**Tiempo estimado:** 10-15 minutos

---

### 2.2 Fraud Detection Engine

**Estado:** ⚠️ Necesita setup y datos

```bash
cd project_2_2_fraud_detection

# Instalar dependencias
pip install pandas numpy scikit-learn xgboost matplotlib seaborn psycopg2-binary

# Paso 1: Preparar datos
python src/preprocess.py

# Paso 2: Entrenar modelos
python src/train_model.py

# Paso 3: Evaluar
python src/evaluate.py
```

**Outputs:**
- Modelos entrenados en `models/`
- Métricas de evaluación
- Predicciones en `results/fraud_scores.csv`

**Modelos generados:**
- Random Forest
- XGBoost
- Ensemble

**Tiempo estimado:** 15-20 minutos

---

### 2.3 Financial Data Warehouse

**Estado:** ⚠️ Necesita setup PostgreSQL

```bash
cd project_2_3_fin_dwh

# Crear BD
createdb fin_dw

# Instalar Python deps
pip install psycopg2-binary pandas sqlalchemy

# Paso 1: Crear schema
psql fin_dw < sql/create_dwh_schema.sql

# Paso 2: Transformaciones
psql fin_dw < sql/transformations.sql

# Paso 3: Cargar datos (Python)
python src/etl_loader.py
```

**Estructura creada:**
- Tablas de dimensiones (dim_*)
- Tablas de hechos (fact_*)
- Vistas materializadas

**Tiempo estimado:** 10 minutos

---

## ⚙️ AUTOMATIZACIÓN

### 3.1 Audit Automation System

**Estado:** ⚠️ Necesita configuración SMTP

```bash
cd project_3_1_audit_automation

# Instalar deps
pip install python-dotenv smtplib

# Crear archivo de configuración
cat > .env << EOF
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_password
FROM_EMAIL=your_email@gmail.com
TO_EMAILS=recipient1@example.com,recipient2@example.com
EOF

# Ejecutar
python src/automator.py --risk-level high

# Con logging
python src/automator.py --risk-level high --log
```

**Ejemplos de salida:**
- Emails clasificados automáticamente
- Plantillas de respuesta generadas

**Tiempo estimado:** 2 minutos

---

### 3.2 Financial Model

**Estado:** ⚠️ Necesita configuración

```bash
cd project_3_2_financial_model

pip install pandas numpy json5

# Ejecutar modelo
python src/financial_model.py --scenario base

# Otros escenarios
python src/financial_model.py --scenario pessimistic
python src/financial_model.py --scenario optimistic
```

**Outputs:**
- Proyecciones financieras
- Análisis de sensibilidad

**Tiempo estimado:** 3 minutos

---

### 3.3 KPI Dashboard Generator

**Estado:** ⚠️ Necesita setup

```bash
cd project_3_3_kpi_dashboard

pip install pandas plotly

# Generar datos de modelo
python src/generate_model_data.py

# Generar dashboard
python src/dashboard_generator.py

# Abrir dashboard
open output/dashboard.html  # macOS
# xdg-open output/dashboard.html  # Linux
```

**KPIs generados:**
- ROA (Return on Assets)
- ROE (Return on Equity)
- Efficiency Ratio
- Coverage Ratio

**Tiempo estimado:** 5 minutos

---

## 🌐 SCRAPING & PARSING

### 4.1 SFC Regulatory Scraper

**Estado:** ✅ Listo para ejecutar

```bash
cd project_4_1_sfc_scraper

# Instalar
pip install requests beautifulsoup4 apscheduler

# Ejecución manual (única vez)
python src/sfc_scraper.py

# Ejecución programada (background)
python src/scheduler.py

# Verificar config
cat src/scheduler.py  # Ver intervals
```

**Funcionalidades:**
- Scrape automático de regulaciones SFC
- Clasificación de categorías
- Email alerts configurables

**Output:**
- `data/regulations.json` - Regulaciones encontradas
- `logs/scraper.log` - Logs de ejecución

**Configurar alerts (opcional):**
```python
# En scheduler.py
SMTP_CONFIG = {
    'server': 'smtp.gmail.com',
    'port': 587,
    'username': 'your_email',
    'password': 'your_password'
}
```

**Tiempo estimado:** 5 minutos

---

### 4.2 Audit CLI Tool

**Estado:** ⚠️ Documento necesario

```bash
cd project_4_2_audit_cli

pip install click pandas

# Ver opciones
python src/cli.py --help

# Ejecutar comando
python src/cli.py audit --type operational
python src/cli.py report --format pdf
```

**Tiempo estimado:** 2 minutos

---

### 4.3 XBRL Parser

**Estado:** ⚠️ Documento necesario

```bash
cd project_4_3_xbrl_parser

pip install lxml pandas

# Parsear archivo XBRL
python src/parser.py --file input.xbrl --output output.csv

# Opciones
python src/parser.py --file report.xbrl --format json
```

**Tiempo estimado:** 1 minuto

---

## 📊 BI & FINANZAS

### 5. Tableau Prep

```bash
cd project_5_tableau_prep

pip install pandas openpyxl

python src/prepare_data.py

# Output: data/prepared_data.csv
# Usar en Tableau
```

---

### 6. IBM Analyst

```bash
cd project_6_ibm_analyst

pip install ibm-watson python-dotenv

cat > .env << EOF
WATSON_API_KEY=your_key
WATSON_URL=https://api.us-south.assistant.watson.cloud.ibm.com
EOF

python src/watson_integration.py
```

---

### 7. Yale Finance Library

```bash
cd project_7_yale_finance

pip install numpy pandas scipy scikit-learn

# Anomalía de mercado
python src/market_anomaly.py

# Optimización de portafolio
python src/portfolio_optimization.py --assets AAPL,MSFT,GOOGL

# Modelo de riesgos
python src/risk_model.py
```

---

### 8. Financial Modeling Suite

```bash
cd project_8_financial_modeling

pip install numpy pandas scipy

# DCF Model
python src/dcf_model.py \
  --growth_rate 0.05 \
  --discount_rate 0.10 \
  --terminal_growth 0.03

# LBO Model
python src/lbo_model.py \
  --purchase_price 100M \
  --debt_ratio 0.70
```

---

### 9. Google BI Infrastructure

```bash
cd project_9_google_bi

pip install pandas google-cloud-bigquery

# Conectar a BigQuery
gsutil config set project your_project_id

# Ejecutar queries
psql < sql/create_views.sql
```

---

## 🤖 IA GENERATIVA

### 10. RAG Financial Assistant

**Estado:** ✅ Listo para ejecutar

```bash
cd project_10_generative_ai

# Instalar dependencias
pip install \
  langchain \
  chromadb \
  openai \
  fastapi \
  uvicorn \
  python-dotenv

# Configurar OpenAI key
export OPENAI_API_KEY="your_key_here"

# O crear .env
cat > .env << EOF
OPENAI_API_KEY=your_key_here
CHROMADB_PATH=./vectorstore
PDF_PATH=./pdfs
EOF

# Iniciar servidor
python src/rag_app.py

# En otra terminal: probar
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "¿Cuál fue la rentabilidad en 2024?"}'

# O usar interfaz web
open http://localhost:8000/ui
```

**Agregar PDFs:**
```bash
# Copiar PDFs a carpeta
cp /path/to/reports.pdf project_10_generative_ai/pdfs/

# Reiniciar para indexar
python src/rag_app.py
```

**Endpoints disponibles:**
- `POST /chat` - Hacer pregunta
- `GET /status` - Estado del sistema
- `POST /documents/upload` - Subir PDF

**Tiempo estimado:** 10 minutos

---

## 🚀 EJECUCIÓN RÁPIDA DE TODOS

```bash
#!/bin/bash
# Script para validar todos los proyectos

echo "🔍 Validando proyectos..."

for project in project_*; do
  echo ""
  echo "━━━━━━━━━━━━━━━━━━━"
  echo "📁 $project"
  echo "━━━━━━━━━━━━━━━━━━━"

  if [ -f "$project/README.md" ]; then
    echo "✅ README encontrado"
  else
    echo "⚠️ README faltante"
  fi

  if [ -f "$project/requirements.txt" ]; then
    echo "✅ requirements.txt encontrado"
  else
    echo "⚠️ requirements.txt faltante"
  fi

  if [ -d "$project/src" ]; then
    echo "✅ Carpeta src encontrada"
    echo "   Archivos: $(find $project/src -type f | wc -l)"
  fi
done

echo ""
echo "✨ Validación completada"
```

Guardar como `validate_all.sh` y ejecutar:
```bash
chmod +x validate_all.sh
./validate_all.sh
```

---

## 📝 NOTAS IMPORTANTES

1. **PostgreSQL:** Varios proyectos lo requieren. Instalar primero:
   ```bash
   # macOS
   brew install postgresql

   # Linux
   sudo apt install postgresql postgresql-contrib
   ```

2. **Python 3.8+:** Asegurar versión correcta
   ```bash
   python --version
   ```

3. **Virtual Environments:** Recomendado
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # o
   venv\Scripts\activate  # Windows
   ```

4. **API Keys:** Proteger credenciales
   - Usar archivos `.env`
   - Nunca commitear a Git
   - Usar variables de entorno

---

## ✅ CHECKLIST DE VALIDACIÓN

- [ ] Clonar/descargar repositorio
- [ ] Instalar Python 3.8+
- [ ] Instalar PostgreSQL (si se usa)
- [ ] Crear virtual environment
- [ ] Ejecutar cada proyecto
- [ ] Revisar outputs
- [ ] Leer README de cada uno
- [ ] Documentar errores encontrados

---

**Última actualización:** 2026-03-10
**Próxima revisión recomendada:** 2026-03-24
