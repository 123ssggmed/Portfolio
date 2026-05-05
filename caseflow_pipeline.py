import pandas as pd
import numpy as np
from datetime import datetime
import os

# --- MOCK AI CLIENT FOR DEMO ---
# En un escenario real, aquí importarías `openai` y harías una llamada a la API
class MockOpenAIClient:
    def extract_case_severity(self, case_notes):
        """
        Simula una llamada a GPT-4 para analizar notas no estructuradas y retornar
        la severidad del caso basado en el contexto médico/legal.
        """
        notes_lower = str(case_notes).lower()
        if any(word in notes_lower for word in ['surgery', 'damage', 'bleeding', 'fractured', 'reconstructive']):
            return 'High'
        elif any(word in notes_lower for word in ['whiplash', 'sprained', 'concussion', 'therapy']):
            return 'Medium'
        else:
            return 'Low'

def run_pipeline():
    print("🚀 Iniciando CaseFlow Analytics Pipeline...")
    
    # 1. EXTRACTION: Cargar los datos crudos
    try:
        leads_df = pd.read_csv('Marketing_Leads.csv')
        cases_df = pd.read_csv('Case_Management.csv')
        print("✅ Datos extraídos de los archivos origen.")
    except FileNotFoundError:
        print("❌ Error: No se encontraron los archivos. Ejecuta 'python generate_mock_data.py' primero.")
        return

    # 2. TRANSFORMATION: Unir los datos (Join CRM + Legal Software)
    df_merged = pd.merge(cases_df, leads_df, on='Lead_ID', how='inner')
    print(f"✅ Datos unificados (Join exitoso): {len(df_merged)} casos encontrados.")

    # 3. CLEANING & MODELING: Creación de métricas de negocio
    df_merged['Open_Date'] = pd.to_datetime(df_merged['Open_Date'])
    df_merged['Settled_Date'] = pd.to_datetime(df_merged['Settled_Date'])
    
    # Días transcurridos hasta ganar el caso
    df_merged['Days_to_Settle'] = (df_merged['Settled_Date'] - df_merged['Open_Date']).dt.days

    # Ingresos de la firma (Los abogados en PI cobran ~33.3% del monto bruto ganado)
    df_merged['Firm_Revenue'] = np.where(df_merged['Status'] == 'Settled', 
                                         df_merged['Gross_Settlement_Amount'] * 0.333, 0)

    # ROI del canal de adquisición
    df_merged['Net_Profit'] = df_merged['Firm_Revenue'] - df_merged['Marketing_Cost']

    # Rellenar valores nulos para evitar errores en BI
    df_merged.fillna({'Gross_Settlement_Amount': 0, 'Days_to_Settle': 0}, inplace=True)
    print("✅ Limpieza y modelado de reglas de negocio completado.")

    # 4. AI WORKFLOW: Extracción de Severidad de Caso
    print("🧠 Procesando notas del abogado con Inteligencia Artificial (LLM)...")
    ai_client = MockOpenAIClient()
    
    # Aplicando AI a los textos no estructurados (En producción -> apply con API real)
    df_merged['AI_Predicted_Severity'] = df_merged['Case_Notes'].apply(ai_client.extract_case_severity)
    print("✅ AI Analysis completado. Clasificación de severidad asignada.")

    # 5. LOAD: Exportación para el Dashboard (Data Warehouse / PowerBI / Excel)
    output_filename = 'CaseFlow_Analytics_Ready.csv'
    df_merged.to_csv(output_filename, index=False)
    print(f"🎉 Pipeline Ejecutado Exitosamente. Datos listos para BI guardados en: {output_filename}\n")

if __name__ == '__main__':
    run_pipeline()
