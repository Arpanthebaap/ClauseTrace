# Skill: Evidence & Citation Skill  *(the reusable, shareable headline skill)*

**Purpose:** Given a question or a scored alert, retrieve the exact supporting transaction
rows **and** the exact regulatory clause(s) that make the finding meaningful — and return
both as first-class, machine-checkable citations rather than free text. This is the skill
that makes every ClauseTrace answer audit-ready, and it is written to be **portable**: any
other CoCo-built copilot in a regulated domain can reuse it by pointing it at its own
transaction table and its own clause-indexed regulatory corpus.

**Reads from:** `raw.transactions`, `analytics.enriched_alerts`, `raw.regulatory_clauses`
(via Cortex Search over the parsed `regs/corpus/` documents)

**Writes to:** `raw.audit_log` (one row per question answered — see schema)

## Contract (what makes it reusable)

This skill takes exactly two typed inputs and returns one typed output, so it can be dropped
into a different domain without touching its internals:

```yaml
inputs:
  entity_ref: string        # e.g. an account_id, alert_id, or free-text question
  clause_topic_hint: string # optional — narrows the regulatory search, e.g. "structuring"
outputs:
  evidence:
    transaction_citations: [ { transaction_id, ts, amount, channel, why_relevant } ]
    clause_citations:      [ { clause_id, source_document, clause_text_excerpt } ]
    confidence: float        # 0-1, degrades toward 0 if either citation list is empty
```

**Reuse rule:** if `transaction_citations` OR `clause_citations` comes back empty, this skill
sets `confidence <= 0.3` and flags `"insufficient_evidence": true` — it never fabricates a
citation to fill the gap. That contract is what the Guardrail Skill checks on every call.

## Retrieval logic
1. Resolve `entity_ref` to a set of transactions (direct account/alert lookup, or — for a
   free-text question — a Cortex Analyst call against the semantic view in
   `sql/003_semantic_view.yaml`).
2. Run Cortex Search over the indexed regulatory corpus using `clause_topic_hint` (or terms
   extracted from the alert's `alert_type`) to retrieve candidate clauses.
3. Re-rank candidate clauses against the actual transaction pattern (e.g. a structuring
   cluster should surface `AML-STR-207` before an unrelated KYC clause).
4. Assemble the typed output above and log the full call to `audit_log`.

## CoCo prompt used to build this skill
> "Build a CoCo skill, Evidence & Citation Skill, with this exact input/output contract
> [pasted above]. It should look up transactions for an entity_ref, run Cortex Search over
> the regulatory clause corpus, re-rank clauses by relevance to the transaction pattern, and
> log every call to raw.audit_log. If either citation list is empty, confidence must drop
> below 0.3 and insufficient_evidence must be true — never invent a citation."

## Publishing note
This skill file is written so a teammate — or a different hackathon team — can reuse it by
swapping `raw.transactions` / `raw.regulatory_clauses` for their own tables and keeping the
same input/output contract. That's the "reusable and shareable skill" bonus the rubric calls
out explicitly.
