import pandas as pd
import numpy as np
import random
from datetime import datetime, timedelta

def create_mock_data():
    np.random.seed(42)
    random.seed(42)

    num_records = 100

    # --- 1. Marketing Leads ---
    lead_ids = [f"L-{1000 + i}" for i in range(num_records)]
    lead_sources = ['Google Ads', 'Referrals', 'Billboards', 'Organic']
    
    # Random date within the last 2 years
    base_date = datetime(2022, 1, 1)
    dates_acquired = [base_date + timedelta(days=random.randint(0, 700)) for _ in range(num_records)]
    
    assigned_sources = random.choices(lead_sources, weights=[0.4, 0.2, 0.2, 0.2], k=num_records)
    
    # Marketing Cost based on source
    marketing_costs = []
    for source in assigned_sources:
        if source == 'Google Ads':
            marketing_costs.append(round(random.uniform(500, 2000), 2))
        elif source == 'Billboards':
            marketing_costs.append(round(random.uniform(1000, 5000), 2))
        elif source == 'Organic':
            marketing_costs.append(0.0)
        else: # Referrals
            marketing_costs.append(round(random.uniform(0, 500), 2))

    leads_df = pd.DataFrame({
        'Lead_ID': lead_ids,
        'Lead_Source': assigned_sources,
        'Date_Acquired': [d.strftime('%Y-%m-%d') for d in dates_acquired],
        'Marketing_Cost': marketing_costs
    })
    
    leads_df.to_csv('Marketing_Leads.csv', index=False)
    print("✅ Created Marketing_Leads.csv")

    # --- 2. Case Management ---
    case_types = ['Car Accident', 'Slip & Fall', 'Medical Malpractice']
    paralegals = ['Sarah Jenkins', 'Mike Torres', 'Jessica Lin', 'David Walsh']
    statuses = ['Open', 'Settled', 'Dropped']

    case_notes_samples = [
        "Client hit by truck at intersection, fractured femur, surgery required, expected long recovery.",
        "Rear-ended at stoplight. Whiplash and mild concussion. Physical therapy ongoing.",
        "Slipped on wet floor in supermarket. Sprained ankle and bruised tailbone.",
        "Misdiagnosed fracture by ER doctor, led to permanent nerve damage.",
        "Minor fender bender. Client complains of back pain but no visible injuries.",
        "Dog bite incident. Severe lacerations on right arm. Requires reconstructive surgery.",
        "T-boned at intersection. Multiple broken ribs and internal bleeding.",
        "Tripped over uneven sidewalk. Scraped knee, minor injuries, likely low payout."
    ]

    case_ids = [f"C-{5000 + i}" for i in range(num_records)]
    selected_case_types = random.choices(case_types, k=num_records)
    selected_paralegals = random.choices(paralegals, k=num_records)
    selected_statuses = random.choices(statuses, weights=[0.3, 0.6, 0.1], k=num_records)

    open_dates = dates_acquired
    settled_dates = []
    gross_settlements = []

    for status, open_date in zip(selected_statuses, open_dates):
        if status == 'Settled':
            days_to_settle = random.randint(90, 450)
            settled_date = open_date + timedelta(days=days_to_settle)
            settled_dates.append(settled_date.strftime('%Y-%m-%d'))
            gross_settlements.append(round(random.uniform(15000, 450000), 2))
        else:
            settled_dates.append(pd.NaT)
            gross_settlements.append(0)

    cases_df = pd.DataFrame({
        'Case_ID': case_ids,
        'Lead_ID': lead_ids,
        'Case_Type': selected_case_types,
        'Paralegal_Assigned': selected_paralegals,
        'Status': selected_statuses,
        'Open_Date': [d.strftime('%Y-%m-%d') for d in open_dates],
        'Settled_Date': settled_dates,
        'Gross_Settlement_Amount': gross_settlements,
        'Case_Notes': random.choices(case_notes_samples, k=num_records)
    })

    cases_df.to_csv('Case_Management.csv', index=False)
    print("✅ Created Case_Management.csv")

if __name__ == '__main__':
    create_mock_data()
