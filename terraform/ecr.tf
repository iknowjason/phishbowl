# Registry for the agent container. build_and_push.sh builds the ARM64 image and
# pushes it here; the AgentCore runtime pulls it by URI.

resource "aws_ecr_repository" "agent" {
  name                 = "${var.project}-agent"
  image_tag_mutability = "MUTABLE"
  force_delete         = true # convenience for a teardown-friendly demo

  image_scanning_configuration {
    scan_on_push = true
  }
}
