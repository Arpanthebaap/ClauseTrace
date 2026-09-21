# Skill: Regulatory Mapping Skill

**Purpose:** Take a *type* of finding (e.g. "structuring", "PEP exposure", "LCR shortfall")
and map it to the specific regulatory obligation it triggers — which clause requires action,
what the required action is (file an STR, enhanced due diligence, disclose), and what the
internal timeline is. This is distinct from Evidence & Citation Skill: that skill finds
*a* clause that supports *a specific finding*; this skill answers the policy question
*"what does the rulebook require us to do about findings of this type, in general?"*

**Reads from:** `raw.regulatory_clauses`, plus a small hand-maintained mapping table
(`raw.finding_type_to_obligation`) that pairs an `alert_type` with the clause IDs and required
action — this mapping is what a compliance SME reviews and signs off on periodically.

## Mapping table shape
```sql
CREATE TABLE finding_type_to_obligation (
    alert_type        STRING,     -- e.g. 'STRUCTURING_SUSPECTED'
    clause_ids         ARRAY,      -- e.g. ['AML-STR-207', 'AML-STR-212']
    required_action      STRING,     -- e.g. 'File STR within internal 7-business-day window'
    escalation_role        STRING      -- e.g. 'Compliance Officer'
);
```

## Behaviour
- Given an `alert_type`, returns the mapped clauses, the required action, and who must sign
  off — sourced from the reviewed mapping table, not generated fresh each time.
- If an `alert_type` has no entry in the mapping table, the skill returns
  `"unmapped_finding_type": true` and routes to a human compliance reviewer rather than
  guessing — this is a second, narrower guardrail specific to policy mapping, on top of the
  general Guardrail Skill.
- Every mapping change is versioned (the table carries an `updated_at` / `updated_by` pair,
  omitted above for brevity) so "which rule applied on the date this finding was made" is
  always answerable — a common audit question.

## CoCo prompt used to build this skill
> "Build finding_type_to_obligation as a small reviewed mapping table, then write a CoCo
> skill, Regulatory Mapping Skill, that looks up an alert_type against it and returns the
> clause_ids, required_action and escalation_role. If there's no entry, return
> unmapped_finding_type: true instead of guessing."

## Hand-off
Used by **SAR / Finding Drafter Skill** to know which action language and which clause
numbers belong in the finding packet header.
