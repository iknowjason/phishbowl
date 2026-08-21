# PhishBowl agent image for Amazon Bedrock AgentCore Runtime.
#
# AgentCore Runtime requires a linux/arm64 image that serves the HTTP contract
# (/invocations + /ping) on port 8080. Build it explicitly for arm64:
#
#   docker buildx build --platform linux/arm64 -t phishbowl-agent:latest --load .
#
# (scripts/build_and_push.sh does this and pushes to ECR.)

FROM --platform=linux/arm64 ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

# Install dependencies first (better layer caching).
COPY pyproject.toml ./
RUN uv sync --no-dev

# App code.
COPY app.py report.py ./
COPY tools ./tools

# Use the resolved virtualenv directly.
ENV PATH="/app/.venv/bin:${PATH}"
ENV PYTHONUNBUFFERED=1

EXPOSE 8080

# Serves /invocations (POST) and /ping (GET) on 0.0.0.0:8080 via BedrockAgentCoreApp.run().
CMD ["python", "app.py"]
