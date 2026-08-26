# Deploying PhishBowl

## Prerequisites

- **AWS account** with permissions to create IAM, ECR, Secrets Manager, SageMaker,
  and Bedrock AgentCore resources.
- **Bedrock model access** enabled in your region: Bedrock console ▸ **Model
  access** ▸ enable the model you'll set as `bedrock_model_id` (default is a Claude
  Sonnet inference profile).
- **Terraform ≥ 1.6** and **AWS provider ≥ 6.51** (first release with the
  `bedrockagentcore_*` resources).
- **Docker with buildx** (the agent image must be `linux/arm64`).
- **A Sublime API key + base URL** — see [sublime-setup.md](sublime-setup.md).
- **AWS credentials** in your shell (`aws sts get-caller-identity` should work).

## 1. Configure variables

```bash
cd terraform
cp example.tfvars secrets.auto.tfvars   # secrets.auto.tfvars is gitignored
$EDITOR secrets.auto.tfvars             # set sublime_api_key, region, model id
```

## 2. Create the ECR repo first

The AgentCore runtime pulls a container image that must already exist, so create
the registry before building:

```bash
terraform init
terraform apply -target=aws_ecr_repository.agent
```

## 3. Build & push the agent image (ARM64)

```bash
cd ..
AWS_REGION=us-east-1 ./scripts/build_and_push.sh
```

This logs in to ECR, builds `agent/` for `linux/arm64`, and pushes `:latest`.

## 4. Apply the rest of the stack

```bash
cd terraform
terraform apply -var-file=secrets.auto.tfvars
```

This creates the Secrets Manager secret, IAM roles, the AgentCore runtime +
endpoint, and the SageMaker notebook. Note the outputs:

```bash
terraform output
# agent_runtime_arn, notebook_open_url, ecr_repository_url, ...
```

## 5. Open the notebook

Use the `notebook_open_url` output (or SageMaker console ▸ Notebook instances ▸
Open Jupyter). Then follow [running.md](running.md).

> If you set `notebook_git_repo`, `phishbowl_triage.ipynb` is already cloned in.
> Otherwise upload `notebook/phishbowl_triage.ipynb` into the Jupyter environment.

## Updating the agent

After changing anything under `agent/`, rebuild and push, then roll the runtime:

```bash
./scripts/build_and_push.sh
cd terraform && terraform apply -var-file=secrets.auto.tfvars
```

(If you push the same `:latest` tag, taint the runtime to force a new version:
`terraform apply -replace=aws_bedrockagentcore_agent_runtime.this ...`, or push a
new `image_tag`.)

## Costs

Rates are us-east-1, verified August 2026. Check the linked pricing pages before
relying on these — AWS changes them.

### Charged while the stack exists

| Resource | Rate | Notes |
|---|---|---|
| SageMaker notebook `ml.t3.medium` | **$0.05 / hour** | Billed while the instance is `InService`, whether or not anyone is using it. ~$36/month if left running. **This dominates the bill.** |
| Secrets Manager | **$0.40 / secret / month** | One secret (`phishbowl/sublime-api-key`), plus $0.05 per 10,000 API calls. |
| ECR storage | **$0.10 / GB-month** | The agent image is ~0.10 GB, so ~$0.01/month. First 500 MB/month is free for the first year on new accounts. |
| S3 (notebook asset) | **$0.023 / GB-month** | One `.ipynb`. Fractions of a cent. |

**Stop the notebook instance when you are not using it.** It is the only resource
here that bills for sitting idle, and it is roughly 97% of the standing cost.
Stopping it (rather than destroying) preserves the EBS volume and your files.

### Charged only when the agent runs

| Resource | Rate | Notes |
|---|---|---|
| AgentCore Runtime | **$0.0895 / vCPU-hour** + **$0.00945 / GB-hour** | Consumption-based with a 1-second minimum. **No idle charge** — a deployed-but-uninvoked runtime costs nothing. A ~10s invocation is a fraction of a cent. |
| Bedrock (Claude Sonnet 4.6) | **$3.00 / M input tokens**, **$15.00 / M output tokens** | Cache reads $0.30/M, cache writes $3.75/M. This dominates per-invocation cost. |

A single triage is mostly Bedrock tokens: the agent reads message headers, links
and bodies, so input tokens scale with `MAX_MESSAGES`. Expect roughly $0.05–$0.25
per run depending on how much mail is in the window — lower `MAX_MESSAGES` and
`LOOKBACK_MINUTES` to cap it.

### Rough monthly totals

| Usage | Estimate |
|---|---|
| Deployed, notebook stopped, no runs | **~$0.41/month** (secret + image storage) |
| Notebook left running 24/7, no runs | **~$36/month** |
| Notebook running 8h/day + 20 triages/day | **~$12 + ~$60 = ~$72/month** |

Pricing sources: [AgentCore](https://aws.amazon.com/bedrock/agentcore/pricing/) ·
[SageMaker](https://aws.amazon.com/sagemaker/pricing/) ·
[ECR](https://aws.amazon.com/ecr/pricing/) ·
[Secrets Manager](https://aws.amazon.com/secrets-manager/pricing/) ·
[Bedrock](https://aws.amazon.com/bedrock/pricing/)

## Teardown

```bash
cd terraform
terraform destroy -var-file=secrets.auto.tfvars
```

`force_delete` on ECR and the 0-day secret recovery window make this clean for a
demo. Raise both for anything production-like.

## Notes / gotchas

- **Region**: keep `aws_region`, the Bedrock model, and the image push all in the
  same region.
- **Model id**: must be exactly a model/inference-profile you've enabled. A
  `AccessDenied`/`ValidationException` on invoke usually means it isn't enabled.
- **Attribute names**: this stack targets AWS provider 6.51+. If `terraform
  validate` flags a `bedrockagentcore` attribute, check the provider docs for that
  version and adjust — the resource surface is young and still settling.
