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
