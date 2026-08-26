<!-- markdownlint-disable MD033 MD041 -->
<h1 align="center">🐟 PhishBowl</h1>

<p align="center">
  <b>A blue-team phishing triage agent on AWS Bedrock AgentCore.</b><br>
  Drop a mailbox in the bowl and let the agent investigate recent suspicious mail —
  headers, links, IPs, and domains — then hand the analyst a confidence-scored report.
</p>

<p align="center">
  <img alt="AWS" src="https://img.shields.io/badge/AWS-Bedrock%20AgentCore-FF9900">
  <img alt="IaC" src="https://img.shields.io/badge/IaC-Terraform-7B42BC">
  <img alt="Agent" src="https://img.shields.io/badge/Agent-Strands-232F3E">
  <img alt="Email" src="https://img.shields.io/badge/Email-Sublime%20Security-3B82F6">
  <img alt="License" src="https://img.shields.io/badge/License-MIT-green">
</p>

---

## What it is

PhishBowl is an open-source demo of an **agentic SOC helper** for email triage. A SOC
analyst opens a **SageMaker Jupyter notebook**, enters a user's email address (or name),
and triggers the workflow. A phishing-triage **agent running on Amazon Bedrock AgentCore**
then:

1. pulls that user's recently received mail from **Sublime Security** (default: the last 5
   minutes; configurable),
2. inspects each message's **headers, links, IP addresses, and domains**,
3. and returns a readable **triage report with per-message confidence levels**.

The entire stack — the AgentCore runtime, the agent's IAM role, the Sublime API secret, and
the analyst's SageMaker notebook — is stood up declaratively with **Terraform**.

> ⚠️ **Demo / educational project.** PhishBowl is built to teach agentic blue-team workflows.
> Verdicts are decision-support, not ground truth — a human analyst stays in the loop.

## Architecture

```
Analyst ─▶ SageMaker Notebook (ml.t3.medium)
            │  input: target user's email / name
            ▼
   boto3 InvokeAgentRuntime ──▶ Bedrock AgentCore Runtime (serverless, ARM64 container)
                                  └─ PhishBowl agent (Strands, on a Bedrock model)
                                      • sublime_fetch_recent  → Sublime /v0/message-groups/search
                                      • sublime_get_message   → full headers / links
                                      • analyze_headers       → SPF/DKIM/DMARC, Reply-To vs From
                                      • analyze_links         → domains, lookalikes, redirects
                                      • analyze_ips           → sender / click-source IP signals
                                  ▼
            Confidence-scored triage report ─▶ rendered in the notebook
   Sublime API key ← AWS Secrets Manager  (read at runtime; never hardcoded)
```

## Repository layout

| Path | What's inside |
|------|---------------|
| `agent/` | The AgentCore container: HTTP entrypoint, Strands agent, triage tools, report builder |
| `terraform/` | ECR, IAM, Secrets Manager, AgentCore runtime + endpoint, SageMaker notebook |
| `notebook/` | `phishbowl_triage.ipynb` — the analyst-facing trigger + report view |
| `scripts/` | `build_and_push.sh` — build the ARM64 image and push to ECR |
| `docs/` | Build, run, and Sublime onboarding guides |

## Quick start

> Full instructions live in [`docs/deploy.md`](docs/deploy.md) and [`docs/running.md`](docs/running.md).

```bash
# 1. Build & push the agent container (ARM64) to ECR
./scripts/build_and_push.sh

# 2. Stand up the infrastructure
cd terraform && terraform init && terraform apply

# 3. Open the SageMaker notebook printed in the Terraform outputs,
#    run phishbowl_triage.ipynb, and enter a target mailbox.
```

## Prerequisites

- An AWS account with Amazon Bedrock model access enabled in your region.
- A **Sublime Security** tenant and an API key ([`docs/sublime-setup.md`](docs/sublime-setup.md)).
- Terraform ≥ 1.6, AWS provider ≥ 6.51 (for the `bedrockagentcore` resources).
- Docker with `buildx` (to build the ARM64 image).

## Costs

The **SageMaker notebook is the only resource that bills while idle** —
`ml.t3.medium` at ~$0.05/hour, about $36/month if you leave it running. Stop the
instance when you are not using it.

AgentCore Runtime is consumption-based with no idle charge, so a deployed agent
costs nothing until invoked; per-run cost is dominated by Bedrock tokens
($3/M in, $15/M out on Claude Sonnet 4.6). Standing cost with the notebook
stopped is roughly **$0.41/month**.

Full breakdown, per-run estimates and pricing sources: [`docs/deploy.md`](docs/deploy.md#costs).

## License

[MIT](LICENSE) © 2026 Jason Ostrom
