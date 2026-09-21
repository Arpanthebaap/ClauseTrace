# Skill: Risk Signal Skill

**Purpose:** Pre-score incoming/open AML & fraud alerts using the rolling account activity
profile and structuring-detection dynamic tables, so an analyst (or the next skill in the
chain) starts from a ranked, explained shortlist instead of a flat alert queue.

**Reads from:** `analytics.enriched_alerts`, `analytics.account_activity_profile`,
`analytics.structuring_signal`

**Writes to:** nothing directly — returns a scored, ranked list to the calling agent /
Streamlit app. (The nightly automation in `sql/004_automation_tasks.sql` persists its own
escalation rows separately.)

## Inputs
- `scope`: `"all_open"` | `"account:<account_id>"` | `"alert:<alert_id>"`
- `min_confidence` (optional, default 0.5): drop signals below this score

## Scoring logic (illustrative, tunable)
```
score = 0.0
+ 0.35 if structuring_signal row exists for the account
+ 0.20 if kyc_risk_rating == 'High'
+ 0.10 if pep_flag is true
+ 0.15 if cross_border_txn_30d >= 3
+ 0.10 if cash_amount_30d > 500000
+ 0.10 if alert_type == 'STRUCTURING_SUSPECTED'
```
Score is clipped to [0, 1] and returned alongside a plain-language reason string built from
whichever factors fired (e.g. *"High KYC risk account with 8 sub-threshold cash deposits
totalling ₹77.5L in 96 hours, 2 cross-border counterparties"*).

## Output shape
```json
{
  "alert_id": "ALRT-...",
  "account_id": "ACC-...",
  "score": 0.82,
  "reason": "...",
  "signals": ["structuring_cluster", "high_kyc_risk", "cross_border_activity"]
}
```

## CoCo prompt used to build this skill
> "Write a CoCo skill called Risk Signal Skill that reads enriched_alerts,
> account_activity_profile and structuring_signal, computes a weighted 0-1 risk score per
> alert using the factors in this table [pasted above], and returns a ranked JSON list with a
> plain-language reason for each score. Make the weights easy to tune in one place."

## Hand-off
Output feeds directly into **Evidence & Citation Skill** — any alert above `min_confidence`
is passed forward with its `account_id` and `alert_id` so the next skill can retrieve the
actual supporting transaction rows and matching regulatory clause.
