# The Sublime API key lives in Secrets Manager. The agent's execution role is the
# only principal allowed to read it; the key is stored as a small JSON blob.

resource "aws_secretsmanager_secret" "sublime" {
  name        = "${var.project}/sublime-api-key"
  description = "Sublime Security API key used by the PhishBowl agent."

  # Demo-friendly: allow immediate re-create after destroy. Raise for production.
  recovery_window_in_days = 0
}

resource "aws_secretsmanager_secret_version" "sublime" {
  secret_id     = aws_secretsmanager_secret.sublime.id
  secret_string = jsonencode({ api_key = var.sublime_api_key })
}
