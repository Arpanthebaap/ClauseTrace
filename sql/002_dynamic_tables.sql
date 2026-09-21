-- ClauseTrace — near-real-time transformation layer
-- Generated/iterated with CoCo CLI: "build a dynamic table that keeps a rolling 24h risk
-- score per account from raw.transactions and raw.alerts, refreshing every 5 minutes"
-- (see docs/coco_cli_playbook.md, Development stage).

USE SCHEMA analytics;

-- Rolling account activity profile: feeds the Risk Signal Skill's scoring.
CREATE OR REPLACE DYNAMIC TABLE account_activity_profile
    TARGET_LAG = '5 minutes'
    WAREHOUSE = clausetrace_wh
AS
SELECT
    a.account_id,
    a.customer_id,
    c.kyc_risk_rating,
    c.pep_flag,
    COUNT(t.transaction_id)                                            AS txn_count_30d,
    SUM(IFF(t.channel = 'Cash Deposit', 1, 0))                          AS cash_txn_count_30d,
    SUM(IFF(t.channel = 'Cash Deposit', t.amount, 0))                    AS cash_amount_30d,
    SUM(IFF(t.counterparty_country NOT IN ('IN'), 1, 0))                  AS cross_border_txn_30d,
    AVG(t.amount)                                                          AS avg_txn_amount_30d,
    MAX(t.ts)                                                              AS last_txn_ts
FROM raw.accounts a
JOIN raw.customers c ON c.customer_id = a.customer_id
LEFT JOIN raw.transactions t
    ON t.account_id = a.account_id
   AND t.ts >= DATEADD('day', -30, CURRENT_TIMESTAMP())
GROUP BY a.account_id, a.customer_id, c.kyc_risk_rating, c.pep_flag;

-- Structuring signal: sub-threshold cash deposits clustering within a rolling 96h window.
-- This is the pattern the Risk Signal Skill surfaces to the analyst first.
CREATE OR REPLACE DYNAMIC TABLE structuring_signal
    TARGET_LAG = '5 minutes'
    WAREHOUSE = clausetrace_wh
AS
SELECT
    account_id,
    COUNT(*)                                    AS cluster_txn_count,
    SUM(amount)                                 AS cluster_total_amount,
    MIN(ts)                                     AS cluster_start,
    MAX(ts)                                     AS cluster_end,
    DATEDIFF('hour', MIN(ts), MAX(ts))          AS cluster_span_hours
FROM raw.transactions
WHERE channel = 'Cash Deposit'
  AND amount BETWEEN 900000 AND 999999          -- illustrative sub-threshold band
  AND ts >= DATEADD('hour', -96, CURRENT_TIMESTAMP())
GROUP BY account_id
HAVING COUNT(*) >= 4;

-- Alert enrichment view joined for the Evidence & Citation Skill to pull from directly.
CREATE OR REPLACE DYNAMIC TABLE enriched_alerts
    TARGET_LAG = '5 minutes'
    WAREHOUSE = clausetrace_wh
AS
SELECT
    al.alert_id,
    al.account_id,
    al.alert_type,
    al.triggered_on,
    al.transaction_count,
    al.total_amount,
    al.status,
    p.kyc_risk_rating,
    p.pep_flag,
    p.cash_amount_30d,
    p.cross_border_txn_30d
FROM raw.alerts al
JOIN account_activity_profile p ON p.account_id = al.account_id;
