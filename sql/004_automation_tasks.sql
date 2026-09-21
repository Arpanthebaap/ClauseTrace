-- ClauseTrace — scheduled automation
-- Generated/iterated with CoCo CLI: "create a scheduled task that re-scores open alerts
-- every night and posts anything newly High-risk to the escalation queue"
-- (docs/coco_cli_playbook.md, "Execution" stage — this is the automation bonus capability).
-- Tasks run under the identity of the user/service role that created them and inherit that
-- role's RBAC, per CoCo's automation model.

USE SCHEMA analytics;

-- Nightly batch: re-run structuring detection + risk scoring over the last 24h of
-- transactions, and write anything newly qualifying into escalation_queue.
CREATE OR REPLACE TABLE escalation_queue (
    escalation_id      STRING DEFAULT UUID_STRING(),
    alert_id            STRING,
    account_id          STRING,
    reason               STRING,
    confidence_score     FLOAT,
    created_at            TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    slack_notified        BOOLEAN DEFAULT FALSE
);

CREATE OR REPLACE TASK nightly_aml_scan
    WAREHOUSE = clausetrace_wh
    SCHEDULE = 'USING CRON 0 2 * * * Asia/Kolkata'   -- 2:00 AM IST daily
AS
INSERT INTO escalation_queue (alert_id, account_id, reason, confidence_score)
SELECT
    ea.alert_id,
    ea.account_id,
    'Nightly scan: open alert on High-risk account with active structuring signal',
    0.87 AS confidence_score
FROM enriched_alerts ea
JOIN structuring_signal ss ON ss.account_id = ea.account_id
WHERE ea.status = 'OPEN'
  AND ea.kyc_risk_rating = 'High'
  AND ea.alert_id NOT IN (SELECT alert_id FROM escalation_queue);

-- Weekly: re-embed/re-index the regulatory corpus so newly added clauses are searchable.
-- (In the CoCo build this calls the document-processing skill against regs/corpus/.)
CREATE OR REPLACE TASK weekly_regulatory_reindex
    WAREHOUSE = clausetrace_wh
    SCHEDULE = 'USING CRON 0 3 * * 1 Asia/Kolkata'   -- Monday 3:00 AM IST
AS
CALL reindex_regulatory_corpus();  -- stored procedure wired to CoCo's document parser

ALTER TASK nightly_aml_scan RESUME;
ALTER TASK weekly_regulatory_reindex RESUME;
