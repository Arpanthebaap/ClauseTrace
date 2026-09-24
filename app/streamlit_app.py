"""
ClauseTrace — Streamlit copilot (local demo build)

Runs entirely offline against the synthetic CSVs produced by
data/generate_synthetic_data.py, mirroring the same Risk Signal -> Evidence & Citation ->
Regulatory Mapping -> Guardrail -> Finding Drafter pipeline the production build runs as
CoCo-orchestrated skills against Snowflake (see skills/*.md and sql/*.sql).

Run:
    cd data && python generate_synthetic_data.py
    cd ../app && streamlit run streamlit_app.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent))
from guardrail import Evidence, verify

DATA_DIR = Path(__file__).parent.parent / "data" / "out"
CORPUS_DIR = Path(__file__).parent.parent / "regs" / "corpus"

# Mirrors sql/... finding_type_to_obligation, kept small & inline for the local demo.
OBLIGATION_MAP = {
    "STRUCTURING_SUSPECTED": {
        "clause_ids": ["AML-STR-207", "AML-STR-212"],
        "required_action": "Escalate for STR review within the internal 7-business-day window.",
        "escalation_role": "Compliance Officer",
    },
    "LARGE_VALUE_TXN": {
        "clause_ids": ["KYC-CDD-104"],
        "required_action": "Confirm transaction is consistent with customer's declared profile; enhanced due diligence if not.",
        "escalation_role": "Level-2 AML Analyst",
    },
}


@st.cache_data
def ensure_data():
    """Auto-generates synthetic data on first run if data/out/ doesn't exist yet.
    This makes the app self-contained for deployment (Streamlit Community Cloud, etc.)
    where data/out/ is gitignored and never present in a fresh checkout."""
    if DATA_DIR.exists() and any(DATA_DIR.glob("*.csv")):
        return
    gen_dir = Path(__file__).parent.parent / "data"
    sys.path.insert(0, str(gen_dir))
    import generate_synthetic_data as gen
    import random

    rng = random.Random(42)
    customers = gen.gen_customers(300, rng)
    accounts = gen.gen_accounts(customers, rng)
    customers_by_id = {c.customer_id: c for c in customers}
    txns, flagged = gen.gen_transactions(accounts, customers_by_id, 90, rng)
    alerts = gen.gen_alerts(txns, flagged, rng)

    gen.write_csv(DATA_DIR / "customers.csv", [c.__dict__ for c in customers])
    gen.write_csv(DATA_DIR / "accounts.csv", [a.__dict__ for a in accounts])
    gen.write_csv(DATA_DIR / "transactions.csv", txns)
    gen.write_csv(DATA_DIR / "alerts.csv", alerts)


@st.cache_data
def load_data():
    customers = pd.read_csv(DATA_DIR / "customers.csv")
    accounts = pd.read_csv(DATA_DIR / "accounts.csv")
    transactions = pd.read_csv(DATA_DIR / "transactions.csv", parse_dates=["ts"])
    alerts = pd.read_csv(DATA_DIR / "alerts.csv")
    return customers, accounts, transactions, alerts


@st.cache_data
def load_corpus():
    clauses = []
    for f in CORPUS_DIR.glob("*.md"):
        text = f.read_text(encoding="utf-8")
        for m in re.finditer(r"## ([\w-]+) — ([^\n]+)\n(.*?)(?=\n## |\Z)", text, re.DOTALL):
            clauses.append({
                "clause_id": m.group(1),
                "title": m.group(2).strip(),
                "text": m.group(3).strip(),
                "source_document": f.name,
            })
    return pd.DataFrame(clauses)


def risk_signal_score(alert_row, accounts, transactions, customers) -> tuple[float, str, list]:
    """Mirrors skills/risk_signal_skill.md scoring logic."""
    acc = accounts[accounts.account_id == alert_row.account_id].iloc[0]
    cust = customers[customers.customer_id == acc.customer_id].iloc[0]
    txns = transactions[transactions.account_id == alert_row.account_id]

    score, signals, reasons = 0.0, [], []
    if alert_row.alert_type == "STRUCTURING_SUSPECTED":
        score += 0.35; signals.append("structuring_cluster")
        reasons.append(f"{alert_row.transaction_count} sub-threshold cash deposits totalling ₹{alert_row.total_amount:,.0f}")
    if cust.kyc_risk_rating == "High":
        score += 0.20; signals.append("high_kyc_risk"); reasons.append("account holder is rated High KYC risk")
    if bool(cust.pep_flag):
        score += 0.10; signals.append("pep"); reasons.append("account holder is flagged PEP")
    cross_border = (txns.counterparty_country != "IN").sum()
    if cross_border >= 3:
        score += 0.15; signals.append("cross_border"); reasons.append(f"{cross_border} cross-border counterparties in the window")
    cash_amt = txns.loc[txns.channel == "Cash Deposit", "amount"].sum()
    if cash_amt > 500000:
        score += 0.10; signals.append("high_cash_volume"); reasons.append(f"₹{cash_amt:,.0f} in cash deposits (30d)")

    score = min(1.0, round(score, 2))
    reason = "; ".join(reasons) if reasons else "No elevated signals beyond the base alert."
    return score, reason, signals


def evidence_and_citation(alert_row, transactions, clauses_df, confidence_base) -> Evidence:
    """Mirrors skills/evidence_citation_skill.md contract."""
    txns = transactions[transactions.account_id == alert_row.account_id]
    if alert_row.alert_type == "STRUCTURING_SUSPECTED":
        relevant = txns[txns.channel == "Cash Deposit"].sort_values("amount", ascending=False).head(8)
    else:
        relevant = txns.sort_values("amount", ascending=False).head(3)

    txn_citations = [
        {"transaction_id": r.transaction_id, "ts": str(r.ts), "amount": r.amount,
         "channel": r.channel, "why_relevant": "part of the flagged pattern" }
        for r in relevant.itertuples()
    ]

    topic_hint = "structuring" if alert_row.alert_type == "STRUCTURING_SUSPECTED" else "due diligence"
    matched = clauses_df[clauses_df.title.str.contains(topic_hint, case=False, na=False) |
                          clauses_df.text.str.contains(topic_hint, case=False, na=False)]
    clause_citations = matched.head(2).to_dict("records")

    confidence = confidence_base
    if not txn_citations or not clause_citations:
        confidence = min(confidence, 0.25)

    return Evidence(transaction_citations=txn_citations, clause_citations=clause_citations, confidence=confidence)


def render_finding_packet(alert_row, score, reason, evidence: Evidence, guardrail_result, obligation):
    st.markdown(f"### Finding Packet — `{alert_row.alert_id}`")
    st.caption(f"Account `{alert_row.account_id}` · {alert_row.alert_type} · status: {alert_row.status}")

    badge_color = {"CITED": "green", "DOWNGRADED": "orange", "INSUFFICIENT_EVIDENCE": "red"}[guardrail_result.verdict]
    st.markdown(f":{badge_color}[**Guardrail verdict: {guardrail_result.verdict}**]  ·  confidence `{evidence.confidence:.2f}`")
    st.info(guardrail_result.message)

    st.markdown("**1. Risk score**")
    st.write(f"`{score:.2f}` — {reason}")

    st.markdown("**2. Evidence — transaction citations**")
    if evidence.transaction_citations:
        st.dataframe(pd.DataFrame(evidence.transaction_citations), hide_index=True, use_container_width=True)
    else:
        st.warning("No transaction citations retrieved.")

    st.markdown("**3. Evidence — regulatory clause citations**")
    if evidence.clause_citations:
        for c in evidence.clause_citations:
            st.markdown(f"> **{c['clause_id']}** — {c['title']}  \n> {c['text'][:280]}{'...' if len(c['text'])>280 else ''}")
    else:
        st.warning("No matching regulatory clause retrieved.")

    st.markdown("**4. Regulatory obligation**")
    if obligation:
        st.write(f"Clauses: {', '.join(obligation['clause_ids'])}")
        st.write(f"Required action: {obligation['required_action']}")
        st.write(f"Escalation role: {obligation['escalation_role']}")
    else:
        st.warning("No mapped obligation for this alert_type — routed to human compliance review.")

    st.markdown("**5. Recommendation**")
    if guardrail_result.show_recommendation:
        st.success(
            f"Recommend escalating `{alert_row.alert_id}` to **{obligation['escalation_role'] if obligation else 'Compliance'}** "
            f"per {', '.join(obligation['clause_ids']) if obligation else 'manual review'}."
        )
    else:
        st.error("Recommendation withheld — see guardrail verdict above.")


def main():
    st.set_page_config(page_title="ClauseTrace", page_icon="🔎", layout="wide")
    st.title("🔎 ClauseTrace")
    st.caption("Evidence-chained Risk, Fraud & Regulatory Intelligence Copilot — local demo build (synthetic data only)")

    if not DATA_DIR.exists():
        with st.spinner("First run: generating synthetic demo data..."):
            ensure_data()

    customers, accounts, transactions, alerts = load_data()
    clauses_df = load_corpus()

    with st.sidebar:
        st.header("Alert queue")
        st.caption(f"{len(alerts)} alerts · {(alerts.status=='OPEN').sum()} open")
        alert_id = st.selectbox("Select an alert to investigate", alerts.alert_id.tolist())
        st.divider()
        st.caption("This mirrors the production skill chain:")
        st.caption("Risk Signal → Evidence & Citation → Regulatory Mapping → Guardrail → Finding Drafter")

    alert_row = alerts[alerts.alert_id == alert_id].iloc[0]

    score, reason, signals = risk_signal_score(alert_row, accounts, transactions, customers)
    confidence_base = 0.55 + 0.35 * score  # illustrative mapping, mirrors skill intent
    evidence = evidence_and_citation(alert_row, transactions, clauses_df, confidence_base)
    guardrail_result = verify(evidence)
    obligation = OBLIGATION_MAP.get(alert_row.alert_type)

    render_finding_packet(alert_row, score, reason, evidence, guardrail_result, obligation)

    st.divider()
    st.subheader("Ask ClauseTrace a question")
    q = st.text_input("e.g. \"Why was this alert flagged?\" or \"What clause covers structuring?\"",
                       value="Why was this alert flagged?")
    if st.button("Ask"):
        if "clause" in q.lower():
            st.write(f"Matched clause(s): {', '.join(c['clause_id'] for c in evidence.clause_citations) or 'none — insufficient evidence'}")
        else:
            st.write(f"{reason} (risk score {score:.2f}, guardrail verdict {guardrail_result.verdict})")
        st.caption("In the production build this call is logged to raw.audit_log with the full evidence object.")


if __name__ == "__main__":
    main()
