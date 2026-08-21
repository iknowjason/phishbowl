# PhishBowl Architecture

PhishBowl is a blue-team phishing **triage** agent. An SOC analyst names a mailbox;
the agent investigates that mailbox's recently received mail and returns a
confidence-scored report. Everything is stood up with Terraform.

## Flow

```
Analyst ─▶ SageMaker Notebook (ml.t3.medium, no local inference)
            │  input: target mailbox + look-back window
            ▼
   boto3 bedrock-agentcore:InvokeAgentRuntime
            │
            ▼
   Bedrock AgentCore Runtime  (serverless, runs an ARM64 container)
     └─ PhishBowl agent (Strands, on a Bedrock model)
         1. sublime_fetch_recent(mailbox, minutes)   → Sublime /v0/message-groups
         2. sublime_get_message(id)                   → headers / links / IPs (parsed)
         3. analyze_headers / analyze_links / analyze_ips  (deterministic signals)
         4. weigh signals → verdict + confidence per message + overall
            │
            ▼
   Structured JSON report ─▶ rendered in the notebook
```

## Components

| Component | What it is | Where |
|-----------|------------|-------|
| **Notebook** | Thin analyst console. Takes input, invokes the runtime, renders the report. Does **no** LLM inference. | `notebook/phishbowl_triage.ipynb` |
| **AgentCore Runtime** | Serverless host for the agent container. Serves the `/invocations` + `/ping` HTTP contract on 8080. | `terraform/agentcore.tf` |
| **Agent** | Strands agent + 5 tools + report contract. | `agent/` |
| **Sublime tools** | Retrieve mail from the Sublime tenant (Bearer auth). | `agent/tools/sublime.py` |
| **Analyzers** | Deterministic header / link / IP signal extraction. | `agent/tools/{headers,links,reputation}.py` |
| **Secret** | Sublime API key in Secrets Manager, read at runtime. | `terraform/secrets.tf` |

## Why the analyzers are deterministic

The header / link / IP tools are plain Python — no model calls. The LLM's job is
**judgement**: it sees the same structured signals a human analyst would (DMARC
fail, brand-lookalike domain, credential-harvest path) and decides verdict +
confidence. This keeps the reasoning auditable and the output reproducible, and it
stops the model from inventing findings the evidence doesn't support.

## Trust & secret boundaries

- The **Sublime API key never lives in the container image or env**. It sits in
  Secrets Manager; the agent's execution role is the only principal that can read
  it, and it's fetched at runtime via `SUBLIME_SECRET_ARN`.
- The **agent role** can only: pull its ECR image, invoke the Bedrock model, read
  that one secret, and write logs.
- The **notebook role** can only: `bedrock-agentcore:InvokeAgentRuntime` on this
  runtime. It cannot read the Sublime secret or call Bedrock directly.
- The runtime ARN reaches the notebook via a lifecycle-config file
  (`~/SageMaker/phishbowl.env`) — never hardcoded.

## Trigger semantics

Requirement calls for "the last 5 minutes." The agent defaults to a **5-minute**
look-back (`created_at[gte] = now - 5m`), but the notebook exposes
`LOOKBACK_MINUTES` and `MAX_MESSAGES` so an analyst can widen the sweep or cap it
for cost/latency.

## This is decision-support

PhishBowl is a teaching/demo project. Verdicts are analyst decision-support, not
final adjudication — a human stays in the loop.
