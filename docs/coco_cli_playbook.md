# CoCo CLI Playbook

This is the log of what to actually **run in CoCo CLI / Desktop** to build ClauseTrace, mapped
to the four lifecycle stages the hackathon rubric grades explicitly: Planning, Development,
Execution, Testing & Validation. Every prompt below is written so you can paste it into CoCo
almost as-is — adjust database/warehouse names to your own account.

Record your actual session (terminal or Desktop) while you run these — that recording *is*
your evidence for "judges will look for evidence of CoCo at every stage." Don't just read this
file on camera; run it.

---

## 1. Planning

Goal: explore the data shape, frame the ontology, and design the semantic view **before**
writing pipeline code.

```
$ coco chat

> I'm building a Risk, Fraud and Regulatory Intelligence Copilot for banking/NBFC AML
> compliance. Help me design the data ontology: Customer -> Account -> Transaction -> Alert
> -> Finding, plus a regulatory clause corpus that findings must cite. What tables do I need,
> and what's the minimum schema for each so a semantic view can answer questions like "which
> accounts show a structuring pattern" and "what clause covers this alert type"?

> Now draft a Snowflake schema for that ontology. I'll review it before you generate anything.

> Given that schema, sketch a semantic view: what metrics matter for an AML analyst, and what
> 4-5 natural-language questions should I write as verified queries to sanity-check it?
```

**Output of this stage:** the ontology and schema draft that became `sql/001_schema.sql`, and
the metric/verified-query list that became `sql/003_semantic_view.yaml`.

---

## 2. Development

Goal: have CoCo generate the pipeline, semantic view, skills, and app — iterated in the CLI,
not hand-written.

```
> Generate the dynamic tables described in our plan: account_activity_profile (rolling 30-day
> activity per account), structuring_signal (cash-deposit clustering), and enriched_alerts
> (alerts joined to the activity profile). Target lag 5 minutes, warehouse clausetrace_wh.

> Now write the semantic view YAML from that schema, including the verified queries we
> sketched in planning.

> Build a CoCo skill called Risk Signal Skill: [paste scoring logic from
> skills/risk_signal_skill.md]. It should read the dynamic tables above and return a ranked,
> scored, ranked JSON list with plain-language reasons.

> Build a second skill, Evidence & Citation Skill, with this exact contract: [paste the
> input/output contract from skills/evidence_citation_skill.md]. It must never fabricate a
> citation — if either citation list is empty, confidence must drop below 0.3.

> Build Regulatory Mapping Skill and SAR / Finding Drafter Skill: [paste specs from the
> respective skill files].

> Build Guardrail / Verifier Skill last: [paste verification logic from
> skills/guardrail_skill.md]. It must only check the evidence it's given, never retrieve
> evidence itself.

> Scaffold a Streamlit app that lets an analyst pick an open alert, runs it through the five
> skills above in order, and renders a finding packet: risk score, transaction citations,
> clause citations, obligation, recommendation (or withheld message), and the guardrail
> verdict. Wire it to Snowsight / Streamlit-in-Snowflake.

> Connect the Slack MCP server and add a post-guardrail step that messages
> #compliance-escalations for any finding with confidence >= 0.7 and verdict != 
> INSUFFICIENT_EVIDENCE. [paste config from mcp/slack_connector.md]
```

**Output of this stage:** `sql/002_dynamic_tables.sql`, `skills/*.md` (as actual CoCo skill
definitions in your workspace), the Snowsight/Streamlit app, and the Slack MCP wiring.

---

## 3. Execution

Goal: run the whole thing end-to-end through CoCo, including a scheduled/automated run.

```
> Run the full pipeline for today's open alerts: Risk Signal Skill, then Evidence & Citation
> Skill, then Regulatory Mapping Skill, then Guardrail Skill, then SAR / Finding Drafter Skill,
> for every OPEN alert in enriched_alerts. Show me the finding packets.

> Create and schedule nightly_aml_scan and weekly_regulatory_reindex as CoCo automations,
> using the cron schedules in sql/004_automation_tasks.sql. Confirm they're RESUMEd and show
> me the next scheduled run time.

> Trigger nightly_aml_scan manually right now so I can see the escalation_queue rows and the
> Slack message it produces.
```

**This is the single "end-to-end workflow executed via CoCo CLI" clip the submission form
asks for** — screen-record this section: an alert going in, the five-skill chain running, and
a finding packet (plus the Slack message) coming out.

---

## 4. Testing & Validation

Goal: prove the guardrail actually holds, and that the semantic view answers real questions
correctly — this is what separates a demo from something a judge trusts.

```
> Run the verified queries in sql/003_semantic_view.yaml against the live semantic view and
> confirm each returns sensible results.

> Generate 5 adversarial test questions for Evidence & Citation Skill: things where the
> honest answer is "no citation exists" (e.g. an alert_type with no mapped regulatory clause,
> or an account with no transaction history). Run them and confirm confidence drops below 0.3
> and insufficient_evidence is true for every one.

> Take one CITED finding packet and manually corrupt one transaction_id reference in the
> draft answer so it no longer matches the evidence. Run it through Guardrail Skill and
> confirm the verdict changes to DOWNGRADED and the corrupted claim is visibly flagged.

> Summarize: out of the test questions above, how many were correctly blocked or downgraded,
> and were there any false CITED verdicts? Show me the audit_log rows for this test run.
```

**Output of this stage:** the pass/fail summary above, and the `audit_log` rows it produced —
both are worth showing on camera as proof the guardrail isn't just described, it's tested.

---

## A note on honesty for judges

Everything in this playbook is written as the actual sequence of prompts to run — not a
post-hoc description of a system that was hand-coded first. If you deviate from this script
while building (you will — that's normal), update this file to match what you actually ran
before recording the demo video, so the video and this playbook agree.
