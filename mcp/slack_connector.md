# MCP connector: Slack escalation

**Purpose:** turn ClauseTrace from a read-only analysis tool into a system that *acts* —
when the nightly automation (`sql/004_automation_tasks.sql`) or a live Guardrail-approved
high-confidence finding lands in `escalation_queue`, CoCo posts it straight to a compliance
Slack channel with the evidence links attached, instead of waiting for someone to check a
dashboard.

## Configuration (CoCo Desktop / CLI)

```jsonc
// .coco/mcp_servers.json (illustrative — replace workspace/channel with your own)
{
  "servers": [
    {
      "name": "slack",
      "transport": "stdio",
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-slack"],
      "env": {
        "SLACK_BOT_TOKEN": "${SLACK_BOT_TOKEN}",
        "SLACK_TEAM_ID": "${SLACK_TEAM_ID}"
      }
    }
  ]
}
```

## What gets posted

Only escalations that already passed the Guardrail Skill (`verdict != INSUFFICIENT_EVIDENCE`)
are eligible to post — the Slack connector calls the `chat.postMessage` tool with a message
built from the finding packet header, never with a freeform, unverified model response:

```
🔴 ClauseTrace escalation — ALRT-37FA2002 (confidence 0.82)
Account ACC-3F56359B4E · STRUCTURING_SUSPECTED
Evidence: 8 cash deposits, ₹77.5L in 96h · Clause AML-STR-207
Required action: Escalate for STR review within 7 business days (Compliance Officer)
→ Open finding packet: <link>
```

## CoCo prompt used to wire this connector
> "Connect the Slack MCP server to CoCo. Add a step after Guardrail Skill that, for any
> escalation_queue row with confidence >= 0.7, posts the finding packet summary above to
> #compliance-escalations using the Slack MCP tool — never post if the guardrail verdict is
> INSUFFICIENT_EVIDENCE."

## Why this counts as the "MCP connector to external tools" bonus
This is genuinely cross-tool action (Snowflake finding → Slack message), gated by the same
guardrail that protects every other surface — the connector doesn't get a separate, looser
trust boundary just because it's an integration.
