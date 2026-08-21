# The PhishBowl agent, hosted on Bedrock AgentCore Runtime.
#
# NOTE: the container image must already exist in ECR before apply — run
# scripts/build_and_push.sh first (see docs/deploy.md).

resource "aws_bedrockagentcore_agent_runtime" "this" {
  agent_runtime_name = replace("${var.project}_agent", "-", "_")
  role_arn           = aws_iam_role.agent.arn
  description        = "PhishBowl phishing-triage agent (Strands on Bedrock)."

  agent_runtime_artifact {
    container_configuration {
      container_uri = "${aws_ecr_repository.agent.repository_url}:${var.image_tag}"
    }
  }

  network_configuration {
    network_mode = "PUBLIC"
  }

  protocol_configuration {
    server_protocol = "HTTP"
  }

  # Injected into the container. The API key itself is NOT here — the agent reads
  # it from Secrets Manager using this ARN.
  environment_variables = {
    SUBLIME_SECRET_ARN = aws_secretsmanager_secret.sublime.arn
    SUBLIME_API_BASE   = var.sublime_api_base
    BEDROCK_MODEL_ID   = var.bedrock_model_id
  }
}

resource "aws_bedrockagentcore_agent_runtime_endpoint" "this" {
  name             = "${var.project}-endpoint"
  agent_runtime_id = aws_bedrockagentcore_agent_runtime.this.agent_runtime_id
  description      = "Default invocation endpoint for the PhishBowl agent."
}
