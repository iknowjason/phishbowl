"""PhishBowl — AgentCore Runtime entrypoint.

Wraps a Strands agent in the Bedrock AgentCore HTTP contract. AgentCore Runtime
runs this container on ARM64 and routes POST /invocations here (plus GET /ping for
health). The analyst's SageMaker notebook calls the runtime via
`bedrock-agentcore InvokeAgentRuntime`, passing a mailbox to triage.

Invocation payload:
    {"mailbox": "user@corp.example", "minutes": 5, "max_messages": 25}

Response:
    {"report": {...structured report...}, "narrative": "<model prose>"}
"""

from __future__ import annotations

import os

from bedrock_agentcore.runtime import BedrockAgentCoreApp
from strands import Agent
from strands.models import BedrockModel

from report import SYSTEM_PROMPT, extract_report
from tools import ALL_TOOLS

# Model is configurable so operators pin whatever they've enabled in Bedrock.
# Must be a model your account has access to in this region (see docs/deploy.md).
MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-6")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")

app = BedrockAgentCoreApp()


def _build_agent() -> Agent:
    model = BedrockModel(
        model_id=MODEL_ID,
        region_name=AWS_REGION,
        temperature=0.2,  # low → deterministic, evidence-anchored triage
    )
    return Agent(model=model, system_prompt=SYSTEM_PROMPT, tools=ALL_TOOLS)


def _prompt(mailbox: str, minutes: int, max_messages: int) -> str:
    return (
        f"Triage the mailbox '{mailbox}'. Investigate messages received in the last "
        f"{minutes} minutes (analyze at most {max_messages}). Follow your workflow, "
        f"then output the JSON report."
    )


@app.entrypoint
def invoke(payload: dict) -> dict:
    """AgentCore invocation handler."""
    mailbox = (payload or {}).get("mailbox") or (payload or {}).get("prompt")
    if not mailbox:
        return {"error": "Provide a 'mailbox' (the target user's email address)."}

    minutes = int((payload or {}).get("minutes", 5))
    max_messages = int((payload or {}).get("max_messages", 25))

    agent = _build_agent()
    result = agent(_prompt(mailbox, minutes, max_messages))
    text = str(result)

    return {
        "report": extract_report(text),
        "narrative": text,
        "model_id": MODEL_ID,
    }


if __name__ == "__main__":
    # Runs a production server on 0.0.0.0:8080 serving /invocations and /ping.
    app.run()
