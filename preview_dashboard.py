import pandas as pd

def generate_preview():
    df = pd.read_csv('CaseFlow_Analytics_Ready.csv')
    
    print("# 📊 Preview del Dashboard: CaseFlow Analytics\n")
    
    # 1. Revenue by Lead Source
    print("## 1. Revenue by Lead Source (¿Qué canal trae más dinero?)")
    rev_by_source = df.groupby('Lead_Source')['Net_Profit'].sum().round(2).sort_values(ascending=False)
    for source, rev in rev_by_source.items():
        print(f"- **{source}**: ${rev:,.2f}")
    print("\n")
    
    # 2. Average Cycle Time by Paralegal
    print("## 2. Average Cycle Time by Paralegal (¿Quién está estancando los casos?)")
    # Solo tomamos casos resueltos
    settled_df = df[df['Status'] == 'Settled']
    cycle_time = settled_df.groupby('Paralegal_Assigned')['Days_to_Settle'].mean().round(1).sort_values(ascending=False)
    for paralegal, days in cycle_time.items():
        print(f"- **{paralegal}**: {days} días promedio")
    print("\n")
    
    # 3. Predictive Pipeline Value
    print("## 3. Predictive Pipeline Value (KPI Card)")
    # Casos abiertos y predicteds como High
    future_pipeline = df[(df['Status'] == 'Open') & (df['AI_Predicted_Severity'] == 'High')]
    # Asumimos un settlement promedio estimado para casos "High" basado en data histórica, o simplemente mostramos el count
    # O calculamos el "Expected Revenue" sumando un valor base. Como no tenemos Gross_Settlement_Amount en Open, asumimos un promedio de casos High ya cerrados
    high_settled = df[(df['Status'] == 'Settled') & (df['AI_Predicted_Severity'] == 'High')]['Firm_Revenue'].mean()
    if pd.isna(high_settled):
        high_settled = 100000 # fallback
    
    predicted_value = len(future_pipeline) * high_settled
    print(f"- **Casos Abiertos de Alta Severidad (AI Evaluated)**: {len(future_pipeline)}")
    print(f"- **Valor Proyectado del Pipeline**: ${predicted_value:,.2f} (Basado en historial de casos severos)")
    print("\n")
    
    # 4. Marketing ROI by Case Type (Heatmap logic)
    print("## 4. Marketing ROI by Case Type (Net Profit distribuido)")
    roi_pivot = df.pivot_table(index='Case_Type', columns='Lead_Source', values='Net_Profit', aggfunc='sum', fill_value=0).round(2)
    print(roi_pivot.to_markdown())
    print("\n")

if __name__ == '__main__':
    generate_preview()
