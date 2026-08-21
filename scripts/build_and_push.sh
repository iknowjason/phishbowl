#!/usr/bin/env bash
#
# Build the PhishBowl agent container for linux/arm64 and push it to ECR.
#
# The ECR repository must exist first. Either:
#   terraform -chdir=terraform apply -target=aws_ecr_repository.agent
# or let this script create nothing and just point at an existing repo.
#
# Usage:
#   AWS_REGION=us-east-1 ./scripts/build_and_push.sh
#
# Env overrides: AWS_REGION, REPO_NAME (default phishbowl-agent), IMAGE_TAG (latest).

set -euo pipefail

REGION="${AWS_REGION:-us-east-1}"
REPO_NAME="${REPO_NAME:-phishbowl-agent}"
TAG="${IMAGE_TAG:-latest}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AGENT_DIR="$(cd "${SCRIPT_DIR}/../agent" && pwd)"

ACCOUNT="$(aws sts get-caller-identity --query Account --output text)"
ECR_HOST="${ACCOUNT}.dkr.ecr.${REGION}.amazonaws.com"
IMAGE="${ECR_HOST}/${REPO_NAME}:${TAG}"

echo ">> Logging in to ECR (${ECR_HOST})"
aws ecr get-login-password --region "${REGION}" \
  | docker login --username AWS --password-stdin "${ECR_HOST}"

echo ">> Building ${IMAGE} for linux/arm64 and pushing"
docker buildx build \
  --platform linux/arm64 \
  --tag "${IMAGE}" \
  --push \
  "${AGENT_DIR}"

echo ">> Done: ${IMAGE}"
echo ">> Now run: terraform -chdir=terraform apply -var-file=secrets.auto.tfvars"
