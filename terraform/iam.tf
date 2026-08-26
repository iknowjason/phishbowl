# ---------------------------------------------------------------------------
# AgentCore runtime execution role
# Assumed by the bedrock-agentcore service. Grants exactly what the container
# needs: pull its image, invoke the Bedrock model, read the Sublime secret,
# and write logs.
# ---------------------------------------------------------------------------

data "aws_iam_policy_document" "agent_assume" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["bedrock-agentcore.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "agent" {
  name               = "${var.project}-agent-runtime"
  assume_role_policy = data.aws_iam_policy_document.agent_assume.json
}

data "aws_iam_policy_document" "agent_permissions" {
  # Pull the container image from ECR.
  statement {
    sid       = "EcrAuth"
    effect    = "Allow"
    actions   = ["ecr:GetAuthorizationToken"]
    resources = ["*"]
  }
  statement {
    sid       = "EcrPull"
    effect    = "Allow"
    actions   = ["ecr:BatchGetImage", "ecr:GetDownloadUrlForLayer"]
    resources = [aws_ecr_repository.agent.arn]
  }

  # Invoke the Bedrock model / inference profile.
  statement {
    sid    = "BedrockInvoke"
    effect = "Allow"
    actions = [
      "bedrock:InvokeModel",
      "bedrock:InvokeModelWithResponseStream",
    ]
    resources = [
      "arn:aws:bedrock:*::foundation-model/*",
      "arn:aws:bedrock:*:${data.aws_caller_identity.current.account_id}:inference-profile/*",
    ]
  }

  # Read the Sublime API key.
  statement {
    sid       = "ReadSublimeSecret"
    effect    = "Allow"
    actions   = ["secretsmanager:GetSecretValue"]
    resources = [aws_secretsmanager_secret.sublime.arn]
  }

  # AgentCore observability / container logs.
  statement {
    sid    = "Logs"
    effect = "Allow"
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents",
      "logs:DescribeLogStreams",
    ]
    resources = ["arn:aws:logs:*:${data.aws_caller_identity.current.account_id}:log-group:/aws/bedrock-agentcore/*"]
  }
}

resource "aws_iam_role_policy" "agent" {
  name   = "${var.project}-agent-permissions"
  role   = aws_iam_role.agent.id
  policy = data.aws_iam_policy_document.agent_permissions.json
}

# ---------------------------------------------------------------------------
# SageMaker notebook execution role
# The analyst's notebook only needs to invoke the AgentCore runtime.
# ---------------------------------------------------------------------------

data "aws_iam_policy_document" "notebook_assume" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["sagemaker.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "notebook" {
  name               = "${var.project}-notebook"
  assume_role_policy = data.aws_iam_policy_document.notebook_assume.json
}

data "aws_iam_policy_document" "notebook_permissions" {
  statement {
    sid    = "InvokeAgentRuntime"
    effect = "Allow"
    actions = [
      "bedrock-agentcore:InvokeAgentRuntime",
    ]
    resources = [
      aws_bedrockagentcore_agent_runtime.this.agent_runtime_arn,
      "${aws_bedrockagentcore_agent_runtime.this.agent_runtime_arn}/*",
    ]
  }

  statement {
    sid    = "ReadNotebookAsset"
    effect = "Allow"
    actions = [
      "s3:GetObject",
    ]
    resources = [
      "${aws_s3_bucket.assets.arn}/notebook/*",
    ]
  }
}

resource "aws_iam_role_policy" "notebook" {
  name   = "${var.project}-notebook-permissions"
  role   = aws_iam_role.notebook.id
  policy = data.aws_iam_policy_document.notebook_permissions.json
}
