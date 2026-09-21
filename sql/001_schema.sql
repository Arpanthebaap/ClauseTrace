-- ClauseTrace — raw schema
-- Built/iterated with CoCo CLI (see docs/coco_cli_playbook.md, "Development" stage).
-- Run in a dedicated database, e.g. CLAUSETRACE_DB.RAW

CREATE SCHEMA IF NOT EXISTS raw;
USE SCHEMA raw;

CREATE OR REPLACE TABLE customers (
    customer_id        STRING PRIMARY KEY,
    name                STRING,
    city                STRING,
    occupation          STRING,
    kyc_risk_rating     STRING,       -- Low | Medium | High
    onboarded_on        DATE,
    pep_flag            BOOLEAN
);

CREATE OR REPLACE TABLE accounts (
    account_id          STRING PRIMARY KEY,
    customer_id         STRING REFERENCES customers(customer_id),
    account_type        STRING,       -- Savings | Current | NRE | Cash Credit
    opened_on           DATE,
    branch_city          STRING
);

CREATE OR REPLACE TABLE transactions (
    transaction_id       STRING PRIMARY KEY,
    account_id           STRING REFERENCES accounts(account_id),
    customer_id          STRING REFERENCES customers(customer_id),
    ts                    TIMESTAMP_NTZ,
    amount                NUMBER(18,2),
    direction             STRING,      -- CREDIT | DEBIT
    channel               STRING,      -- NEFT | RTGS | IMPS | UPI | Cash Deposit | Cheque | Wire
    counterparty_country  STRING,      -- ISO-2, illustrative
    narrative             STRING
);

CREATE OR REPLACE TABLE alerts (
    alert_id              STRING PRIMARY KEY,
    account_id            STRING REFERENCES accounts(account_id),
    alert_type            STRING,      -- STRUCTURING_SUSPECTED | LARGE_VALUE_TXN | ...
    triggered_on          TIMESTAMP_NTZ,
    transaction_count     NUMBER,
    total_amount          NUMBER(18,2),
    status                 STRING       -- OPEN | UNDER_REVIEW | CLEARED | ESCALATED | STR_FILED
);

-- Regulatory clause index (populated by CoCo's document-processing step over regs/corpus/)
CREATE OR REPLACE TABLE regulatory_clauses (
    clause_id             STRING PRIMARY KEY,   -- e.g. AML-STR-207
    source_document       STRING,
    topic                  STRING,
    clause_text            STRING,
    effective_from          DATE
);

-- Immutable audit log — every question asked, evidence retrieved, citation used,
-- confidence score, and which skill/agent produced the answer.
CREATE OR REPLACE TABLE audit_log (
    audit_id               STRING PRIMARY KEY,
    asked_at                TIMESTAMP_NTZ,
    asked_by                STRING,
    question                 STRING,
    evidence_transaction_ids ARRAY,
    evidence_clause_ids       ARRAY,
    confidence_score          FLOAT,
    guardrail_verdict          STRING,   -- CITED | INSUFFICIENT_EVIDENCE | DOWNGRADED
    answer_text                STRING,
    responding_skill            STRING
);
