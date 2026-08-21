# The analyst's Jupyter environment — a small managed notebook that does NO local
# inference. It only takes a mailbox as input and invokes the AgentCore runtime.

# On start, drop the runtime coordinates where the notebook can read them, so the
# .ipynb never hardcodes an ARN.
locals {
  # No nested heredoc: write the env file line by line so Terraform's indented-
  # heredoc stripping can't corrupt an inner delimiter.
  on_start = <<-BASH
    #!/bin/bash
    set -euo pipefail
    ENVFILE=/home/ec2-user/SageMaker/phishbowl.env
    {
      echo "PHISHBOWL_RUNTIME_ARN=${aws_bedrockagentcore_agent_runtime.this.agent_runtime_arn}"
      echo "PHISHBOWL_ENDPOINT_NAME=${aws_bedrockagentcore_agent_runtime_endpoint.this.name}"
      echo "AWS_REGION=${var.aws_region}"
    } > "$ENVFILE"
    chown ec2-user:ec2-user "$ENVFILE" || true
  BASH
}

resource "aws_sagemaker_notebook_instance_lifecycle_configuration" "this" {
  name      = "${var.project}-lifecycle"
  on_start  = base64encode(local.on_start)
}

# Optional: clone the repo so phishbowl_triage.ipynb is already present.
resource "aws_sagemaker_code_repository" "this" {
  count                = var.notebook_git_repo == "" ? 0 : 1
  code_repository_name = "${var.project}-repo"

  git_config {
    repository_url = var.notebook_git_repo
  }
}

resource "aws_sagemaker_notebook_instance" "this" {
  name                    = "${var.project}-notebook"
  instance_type           = var.notebook_instance_type
  role_arn                = aws_iam_role.notebook.arn
  lifecycle_config_name   = aws_sagemaker_notebook_instance_lifecycle_configuration.this.name
  volume_size             = 10
  default_code_repository = var.notebook_git_repo == "" ? null : aws_sagemaker_code_repository.this[0].code_repository_name
}
