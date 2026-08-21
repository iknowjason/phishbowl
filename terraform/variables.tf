variable "aws_region" {
  description = "AWS region to deploy PhishBowl into. Must have Bedrock model access enabled."
  type        = string
  default     = "us-east-1"
}

variable "project" {
  description = "Short project/name prefix for all resources."
  type        = string
  default     = "phishbowl"
}

variable "sublime_api_key" {
  description = "Sublime Security API key. Stored in Secrets Manager; never hardcoded in the agent."
  type        = string
  sensitive   = true
}

variable "sublime_api_base" {
  description = "Sublime Platform API base URL. Confirm your tenant's value in the Sublime console."
  type        = string
  default     = "https://api.platform.sublime.security"
}

variable "bedrock_model_id" {
  description = "Bedrock model id (or inference profile) the agent uses. Must be enabled in your account/region."
  type        = string
  default     = "us.anthropic.claude-sonnet-4-20250514-v1:0"
}

variable "image_tag" {
  description = "ECR image tag for the agent container (set by scripts/build_and_push.sh)."
  type        = string
  default     = "latest"
}

variable "notebook_instance_type" {
  description = "SageMaker notebook instance type. ml.t3.medium is a plain 2-vCPU box (no GPU); smallest/cheapest."
  type        = string
  default     = "ml.t3.medium"
}

variable "notebook_git_repo" {
  description = "Optional HTTPS git URL cloned into the notebook (so phishbowl_triage.ipynb is present). Leave empty to upload the notebook manually."
  type        = string
  default     = ""
}
