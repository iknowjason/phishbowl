# Copy to a private tfvars file (e.g. secrets.auto.tfvars — gitignored) and fill in.
#   terraform apply -var-file=secrets.auto.tfvars

aws_region       = "us-east-1"
sublime_api_key  = "REPLACE_WITH_YOUR_SUBLIME_API_KEY"
sublime_api_base = "https://platform.sublime.security"

# Must be enabled in Bedrock ▸ Model access for your region:
bedrock_model_id = "us.anthropic.claude-sonnet-4-6"

# Optional: clone the repo into the notebook so phishbowl_triage.ipynb is present.
# notebook_git_repo = "https://github.com/<you>/phishbowl.git"
