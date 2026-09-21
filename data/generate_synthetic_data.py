"""
ClauseTrace — synthetic data generator.

Generates fully synthetic, referentially-consistent Customer -> Account -> Transaction ->
Alert data plus a sanctions/watchlist stub, so the whole prototype can be built, demoed and
graded WITHOUT touching any real customer or transaction data.

In the actual CoCo build this same generation step is done *inside CoCo CLI* with a prompt
like:

    "Generate a synthetic banking dataset: 500 customers with KYC risk ratings, 800 accounts,
     40,000 transactions over 90 days with realistic structuring/smurfing patterns injected
     for ~3% of accounts, and an AML alert queue referencing those transactions. Keep it
     referentially consistent and write it out as Snowflake tables."

This script is the local, offline, reviewable equivalent — run it directly, or use it as the
spec CoCo mirrors when generating the same data as Snowflake tables (see sql/001_schema.sql
and docs/coco_cli_playbook.md, "Planning" and "Development" sections).

Usage:
    python generate_synthetic_data.py [--seed 42] [--customers 500] [--days 90]

Output: CSV files written to ./out/
"""
from __future__ import annotations

import argparse
import csv
import random
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

FIRST_NAMES = ["Aarav", "Vivaan", "Aditi", "Diya", "Kabir", "Meera", "Rohan", "Isha",
               "Arjun", "Priya", "Sanjay", "Neha", "Karan", "Ananya", "Vikram", "Pooja",
               "Rahul", "Simran", "Aditya", "Kavya"]
LAST_NAMES = ["Sharma", "Verma", "Iyer", "Reddy", "Nair", "Gupta", "Mehta", "Kapoor",
              "Chatterjee", "Rao", "Joshi", "Malhotra", "Bose", "Pillai", "Khan", "Singh"]
CITIES = ["Mumbai", "Bengaluru", "Delhi NCR", "Pune", "Hyderabad", "Chennai", "Kolkata",
          "Durgapur", "Ahmedabad", "Jaipur"]
OCCUPATIONS = ["Salaried - IT", "Salaried - Manufacturing", "Self-employed - Trading",
               "Self-employed - Consulting", "Business Owner - Retail", "Student",
               "Retired", "Homemaker", "NRI - Remittance"]
CHANNELS = ["NEFT", "RTGS", "IMPS", "UPI", "Cash Deposit", "Cheque", "Wire - Cross Border"]
COUNTERPARTY_COUNTRIES = ["IN", "IN", "IN", "IN", "AE", "SG", "US", "GB", "HK", "CY"]
HIGH_RISK_COUNTRIES = {"CY", "HK"}  # illustrative only, not a real watchlist


@dataclass
class Customer:
    customer_id: str
    name: str
    city: str
    occupation: str
    kyc_risk_rating: str
    onboarded_on: str
    pep_flag: bool = False


@dataclass
class Account:
    account_id: str
    customer_id: str
    account_type: str
    opened_on: str
    branch_city: str


def gen_customers(n: int, rng: random.Random) -> list[Customer]:
    customers = []
    for _ in range(n):
        name = f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}"
        risk = rng.choices(["Low", "Medium", "High"], weights=[70, 24, 6])[0]
        onboarded = datetime(2019, 1, 1) + timedelta(days=rng.randint(0, 2500))
        customers.append(Customer(
            customer_id=f"CUST-{uuid.uuid4().hex[:8].upper()}",
            name=name,
            city=rng.choice(CITIES),
            occupation=rng.choice(OCCUPATIONS),
            kyc_risk_rating=risk,
            onboarded_on=onboarded.date().isoformat(),
            pep_flag=rng.random() < 0.015,
        ))
    return customers


def gen_accounts(customers: list[Customer], rng: random.Random) -> list[Account]:
    accounts = []
    for c in customers:
        for _ in range(rng.choices([1, 2, 3], weights=[60, 30, 10])[0]):
            accounts.append(Account(
                account_id=f"ACC-{uuid.uuid4().hex[:10].upper()}",
                customer_id=c.customer_id,
                account_type=rng.choice(["Savings", "Current", "NRE", "Cash Credit"]),
                opened_on=c.onboarded_on,
                branch_city=c.city,
            ))
    return accounts


def gen_transactions(accounts: list[Account], customers_by_id: dict, days: int, rng: random.Random):
    """Generates normal activity, then injects a handful of structuring/smurfing patterns
    into ~3% of accounts so the alert queue and demo have real signal to find."""
    txns = []
    start = datetime.today() - timedelta(days=days)

    for acc in accounts:
        cust = customers_by_id[acc.customer_id]
        base_amt = rng.choice([5000, 12000, 25000, 60000, 150000])
        n_txn = rng.randint(15, 90)
        for _ in range(n_txn):
            ts = start + timedelta(days=rng.randint(0, days), hours=rng.randint(0, 23),
                                     minutes=rng.randint(0, 59))
            amt = round(base_amt * rng.uniform(0.2, 2.2), 2)
            txns.append(dict(
                transaction_id=f"TXN-{uuid.uuid4().hex[:12].upper()}",
                account_id=acc.account_id,
                customer_id=acc.customer_id,
                ts=ts.isoformat(timespec="seconds"),
                amount=amt,
                direction=rng.choice(["CREDIT", "DEBIT"]),
                channel=rng.choice(CHANNELS),
                counterparty_country=rng.choices(COUNTERPARTY_COUNTRIES, weights=[40, 20, 15, 10, 5, 4, 3, 1, 1, 1])[0],
                narrative=rng.choice(["Salary credit", "Vendor payment", "Family transfer",
                                       "Utility bill", "Invoice settlement", "Investment",
                                       "Loan EMI", "Retail purchase settlement"]),
            ))

    # inject structuring pattern into ~3% of accounts: many sub-threshold cash deposits
    # in a short window, just under a synthetic reporting threshold of 1,000,000 (illustrative)
    flagged_accounts = rng.sample(accounts, max(1, len(accounts) // 33))
    for acc in flagged_accounts:
        cluster_start = start + timedelta(days=rng.randint(0, max(1, days - 5)))
        for i in range(rng.randint(6, 11)):
            ts = cluster_start + timedelta(hours=rng.randint(0, 96))
            txns.append(dict(
                transaction_id=f"TXN-{uuid.uuid4().hex[:12].upper()}",
                account_id=acc.account_id,
                customer_id=acc.customer_id,
                ts=ts.isoformat(timespec="seconds"),
                amount=round(rng.uniform(920000, 998000), 2),
                direction="CREDIT",
                channel="Cash Deposit",
                counterparty_country="IN",
                narrative="Cash deposit",
            ))

    txns.sort(key=lambda t: t["ts"])
    return txns, {a.account_id for a in flagged_accounts}


def gen_alerts(txns, flagged_accounts, rng: random.Random):
    alerts = []
    # one alert per flagged account, referencing its cluster of cash deposits
    by_acc = {}
    for t in txns:
        by_acc.setdefault(t["account_id"], []).append(t)

    for acc_id in flagged_accounts:
        cluster = [t for t in by_acc[acc_id] if t["narrative"] == "Cash deposit"]
        total = round(sum(t["amount"] for t in cluster), 2)
        alerts.append(dict(
            alert_id=f"ALRT-{uuid.uuid4().hex[:8].upper()}",
            account_id=acc_id,
            alert_type="STRUCTURING_SUSPECTED",
            triggered_on=max(t["ts"] for t in cluster),
            transaction_count=len(cluster),
            total_amount=total,
            status="OPEN",
        ))

    # noise: plausible-looking but benign alerts (the false-positive majority)
    normal_accounts = list(by_acc.keys() - set(flagged_accounts))
    for acc_id in rng.sample(normal_accounts, min(len(normal_accounts), max(5, len(normal_accounts) // 6))):
        cand = [t for t in by_acc[acc_id] if t["amount"] > 400000]
        if not cand:
            continue
        t = rng.choice(cand)
        alerts.append(dict(
            alert_id=f"ALRT-{uuid.uuid4().hex[:8].upper()}",
            account_id=acc_id,
            alert_type="LARGE_VALUE_TXN",
            triggered_on=t["ts"],
            transaction_count=1,
            total_amount=t["amount"],
            status="OPEN",
        ))

    return alerts


def write_csv(path: Path, rows: list[dict]):
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {len(rows):>6} rows -> {path}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--customers", type=int, default=500)
    ap.add_argument("--days", type=int, default=90)
    ap.add_argument("--out", type=str, default="out")
    args = ap.parse_args()

    rng = random.Random(args.seed)
    out = Path(__file__).parent / args.out

    customers = gen_customers(args.customers, rng)
    accounts = gen_accounts(customers, rng)
    customers_by_id = {c.customer_id: c for c in customers}
    txns, flagged = gen_transactions(accounts, customers_by_id, args.days, rng)
    alerts = gen_alerts(txns, flagged, rng)

    write_csv(out / "customers.csv", [c.__dict__ for c in customers])
    write_csv(out / "accounts.csv", [a.__dict__ for a in accounts])
    write_csv(out / "transactions.csv", txns)
    write_csv(out / "alerts.csv", alerts)

    print(f"\n{len(flagged)} accounts carry an injected structuring pattern "
          f"(ground truth for demo + guardrail testing).")
    print("Done. This data is 100% synthetic \u2014 no real customer or transaction data.")


if __name__ == "__main__":
    main()
