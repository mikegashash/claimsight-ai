import pandas as pd
import numpy as np
from faker import Faker
import os

fake = Faker()

N = 2000
claims = []
for i in range(N):
    claims.append({
        "claim_id": f"C{i:05d}",
        "policy_id": f"P{np.random.randint(1000,9999)}",
        "loss_dt": fake.date_this_decade(),
        "loss_type": np.random.choice(["fire", "water", "theft", "collision"]),
        "amount": round(np.random.uniform(500, 50000), 2),
        "zip": fake.zipcode(),
        "provider_id": f"PR{np.random.randint(100,999)}",
        "claimant_history_count": np.random.randint(0,5),
        "fraud_flag": np.random.choice([0,1], p=[0.9, 0.1])
    })

df = pd.DataFrame(claims)
os.makedirs("data", exist_ok=True)
df.to_csv("data/claims.csv", index=False)
print(f"Generated {len(df)} synthetic claims in data/claims.csv")
