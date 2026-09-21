# Skill: Guardrail / Verifier Skill

**Purpose:** The last stop before any answer reaches a user. Verifies that every factual claim
in a draft answer is backed by a citation returned from `Evidence & Citation Skill`, and
either passes the answer through, downgrades it with a visible caveat, or blocks it entirely.
This is what makes ClauseTrace fail *safely* instead of hallucinating a plausible-looking but
unsupported citation — the single biggest trust risk for a regulatory copilot.

**Reads from:** the draft answer + the `evidence` object produced by
`Evidence & Citation Skill` for the same request (never re-derives evidence itself — it only
checks what was actually retrieved, so it can't be talked into approving a claim on the
strength of its own reasoning).

## Verification logic
```
for each factual claim in the draft answer:
    if claim references a transaction_id -> must appear in evidence.transaction_citations
    if claim references a clause_id      -> must appear in evidence.clause_citations
    if claim has no matching citation    -> mark as UNSUPPORTED

if any UNSUPPORTED claims exist:
    if evidence.confidence >= 0.5  -> verdict = DOWNGRADED   (answer shown with a visible
                                        caveat, unsupported sentences struck or flagged)
    else                              -> verdict = INSUFFICIENT_EVIDENCE (answer withheld,
                                        user is told plainly why and what would help,
                                        e.g. "no matching regulatory clause found for this
                                        alert_type — routed to manual review")
else:
    verdict = CITED   (answer passes through unchanged)
```

Every verdict, along with the input answer and the evidence it was checked against, is
written to `raw.audit_log` — so a reviewer can later see not just what the system said, but
what it *refused* to say and why.

## Why this is a distinct skill (not folded into Evidence & Citation Skill)
Separating retrieval (Evidence & Citation Skill) from verification (this skill) means the
verifier has no incentive to find supporting evidence — it only checks what was already
found. This hand-off is the core of the multi-agent pattern: **Analyst Agent → Citation Agent
→ Guardrail Agent**, each with a narrower job than the one before it.

## CoCo prompt used to build this skill
> "Write Guardrail / Verifier Skill. It takes a draft answer and the evidence object from
> Evidence & Citation Skill, checks every transaction_id / clause_id reference against what
> was actually retrieved, and returns CITED, DOWNGRADED, or INSUFFICIENT_EVIDENCE using the
> logic above. Log every verdict with the full answer and evidence to raw.audit_log. It must
> never call retrieval itself — only verify what it's given."

## Test cases used to validate this skill (Testing & Validation stage)
1. A fully-cited answer → expect `CITED`, unchanged.
2. An answer with one fabricated `transaction_id` mixed into otherwise-cited claims →
   expect `DOWNGRADED`, and confirm the fabricated sentence is visibly flagged.
3. A question about an `alert_type` with no mapped regulatory clause → expect
   `INSUFFICIENT_EVIDENCE`, and confirm the user-facing message names the actual gap instead
   of a generic error.
