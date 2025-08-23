import os, random, pandas as pd
from datetime import datetime, timedelta
random.seed(42)

N = 2000
LOB = ["Auto","Home","WorkersComp","GL"]
STATES = ["NY","NJ","PA","OH","IL","MI","FL","TX","CA","GA","NC","VA","WA","MA","AZ","CO"]
INJ = ["None","Minor","Moderate","Severe","Fatal"]
REPAIR_SHOPS = [f"RS{str(i).zfill(4)}" for i in range(1,301)]
PROVIDERS = [f"PR{str(i).zfill(4)}" for i in range(1,401)]
suspect_providers = set(random.sample(PROVIDERS, 10))
suspect_shops = set(random.sample(REPAIR_SHOPS, 8))

def rdate():
    a = datetime(2018,1,1); b = datetime(2025,8,1)
    return a + timedelta(days=random.randrange((b-a).days))

rows=[]
for i in range(N):
    lob = random.choices(LOB, weights=[0.55,0.2,0.15,0.1])[0]
    incident = rdate()
    delay = int(abs(random.gauss(5,7)))
    report = incident + timedelta(days=delay)
    injury = random.choices(INJ, weights=[0.55,0.22,0.16,0.06,0.01])[0]
    police = 1 if random.random() < (0.8 if lob=="Auto" else 0.35) else 0
    base = {"Auto":3500,"Home":12000,"WorkersComp":18000,"GL":15000}[lob]
    sev_mult = {"None":0.7,"Minor":1.0,"Moderate":1.6,"Severe":3.0,"Fatal":8.0}[injury]
    amount = float(int(base*sev_mult*random.uniform(0.6,1.6)))
    paid = float(int(amount*random.uniform(0.1,0.9)))
    reserve = float(int(max(0, amount*random.uniform(0.0,0.6)-paid*0.1)))
    provider = random.choice(PROVIDERS) if lob!="Home" else ""
    shop = random.choice(REPAIR_SHOPS) if lob=="Auto" else ""
    rows.append({
        "claim_id": f"C{str(i+1).zfill(6)}",
        "policy_id": f"P{str(random.randint(1,6000)).zfill(6)}",
        "line_of_business": lob,
        "state": random.choice(STATES),
        "incident_date": incident.date().isoformat(),
        "report_date": report.date().isoformat(),
        "late_report_days": delay,
        "claim_amount": amount,
        "paid_to_date": paid,
        "reserve": reserve,
        "claimant_age": max(18,min(90,int(random.gauss(42,12)))),
        "injury_severity": injury,
        "police_report": police,
        "prior_claims_count": max(0,int(random.gauss(0.6,1.0))),
        "vehicle_make": "",
        "vin": "",
        "provider_id": provider,
        "repair_shop_id": shop
    })
os.makedirs("data", exist_ok=True)
pd.DataFrame(rows).to_csv("data/synthetic_claims.csv", index=False)
print("Wrote data/synthetic_claims.csv")
