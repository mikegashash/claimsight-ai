import os, textwrap, random
os.makedirs("data/policies", exist_ok=True)

TEMPLATE = """\
POLICY {pid} — Standard Homeowners (HO-3)

Section 1: Dwelling (Coverage A)
We cover sudden and accidental direct physical loss to the dwelling unless excluded.
Water backup from sewers or drains is EXCLUDED unless an endorsement applies.

Section 2: Other Structures (Coverage B)
We cover other structures on the residence premises.

Section 3: Personal Property (Coverage C)
Theft is covered subject to limits and exclusions.

Section 4: Perils Insured Against
Fire, lightning, windstorm, hail are covered causes of loss.
Flood is EXCLUDED. Wear and tear EXCLUDED.

Section 5: Endorsements
{endorsements}

Section 6: Conditions
Insured must provide prompt notice and cooperate with investigation.
"""

ENDORSEMENTS = [
    "Water Backup Endorsement: Water/sewer backup losses up to $10,000 are covered.",
    "Special Personal Property: Broadens perils for Coverage C.",
    "Identity Theft Expense Endorsement: Limited reimbursement."
]

for i in range(1, 6):
    chosen = random.sample(ENDORSEMENTS, k=random.randint(1, len(ENDORSEMENTS)))
    with open(f"data/policies/policy_{i:02d}.txt", "w") as f:
        f.write(TEMPLATE.format(pid=i, endorsements="\n".join(f"- {e}" for e in chosen)))

print("Generated sample policies in data/policies/")
