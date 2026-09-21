# Skill: SAR / Finding Drafter Skill

**Purpose:** Assemble the outputs of the three skills above into a single, human-readable,
audit-ready **finding packet** — the document a Compliance Officer actually reviews and signs,
and the artifact that answers "why did we clear/escalate this?" months later.

**Reads from:** outputs of `Risk Signal Skill`, `Evidence & Citation Skill`,
`Regulatory Mapping Skill` for a given `alert_id` — never touches raw tables directly, by
design, so the packet can only ever contain claims that already passed through citation and
guardrail checks upstream.

## Finding packet structure
```
1. Header:        alert_id, account_id, alert_type, date range, analyst/system
2. Risk score:     score + plain-language reason (from Risk Signal Skill)
3. Evidence:       transaction_citations table + clause_citations table
                    (from Evidence & Citation Skill — rendered verbatim, not paraphrased)
4. Obligation:     required_action + escalation_role
                    (from Regulatory Mapping Skill)
5. Recommendation: draft narrative connecting evidence -> obligation -> recommended action
6. Confidence & guardrail verdict: shown to the reviewer, not hidden
7. Sign-off block: reviewer name, decision, timestamp (added by the human, not the model)
```

## Guardrail interaction
This skill will **not** render section 5 (the recommendation narrative) if the Guardrail
Skill's verdict for this alert is `INSUFFICIENT_EVIDENCE` — the packet still generates, but
section 5 is replaced with: *"Recommendation withheld: evidence does not meet the citation
threshold. Route to manual review."* This keeps a human in the loop exactly where the system
is least confident, instead of forcing a low-confidence recommendation into the packet.

## Output format
Rendered as Markdown (for the Streamlit preview) and exported as PDF for the analyst to
attach to the case file — this is the literal "audit ready regulatory output from natural
language questions" the challenge brief asks for.

## CoCo prompt used to build this skill
> "Build SAR / Finding Drafter Skill: take the outputs of the three upstream skills for one
> alert_id and render the 7-section finding packet in the structure above, in Markdown. If
> guardrail_verdict is INSUFFICIENT_EVIDENCE, replace section 5 with the withheld-recommendation
> message instead of generating a recommendation. Add a PDF export."
