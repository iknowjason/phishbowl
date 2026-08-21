output "ecr_repository_url" {
  description = "Push the agent image here (used by scripts/build_and_push.sh)."
  value       = aws_ecr_repository.agent.repository_url
}

output "agent_runtime_arn" {
  description = "AgentCore runtime ARN the notebook invokes."
  value       = aws_bedrockagentcore_agent_runtime.this.agent_runtime_arn
}

output "agent_runtime_id" {
  description = "AgentCore runtime id."
  value       = aws_bedrockagentcore_agent_runtime.this.agent_runtime_id
}

output "agent_runtime_endpoint_name" {
  description = "AgentCore runtime endpoint name."
  value       = aws_bedrockagentcore_agent_runtime_endpoint.this.name
}

output "sublime_secret_arn" {
  description = "Secrets Manager ARN holding the Sublime API key."
  value       = aws_secretsmanager_secret.sublime.arn
}

output "notebook_name" {
  description = "SageMaker notebook instance name."
  value       = aws_sagemaker_notebook_instance.this.name
}

output "notebook_open_url" {
  description = "Console URL to open the analyst notebook (Jupyter)."
  value       = "https://${var.aws_region}.console.aws.amazon.com/sagemaker/home?region=${var.aws_region}#/notebook-instances/openNotebook/${aws_sagemaker_notebook_instance.this.name}?view=classic"
}
