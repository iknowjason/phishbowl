terraform {
  required_version = ">= 1.6.0"

  required_providers {
    aws = {
      source = "hashicorp/aws"
      # 6.51+ is the first release with the bedrockagentcore_* resources.
      version = ">= 6.51.0"
    }
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project   = var.project
      ManagedBy = "terraform"
      Repo      = "phishbowl"
    }
  }
}

data "aws_caller_identity" "current" {}
data "aws_region" "current" {}
