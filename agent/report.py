"""The triage report contract.

Holds the agent's system prompt, the JSON schema it must emit, and a resilient
extractor that recovers that JSON from the model's final message. Keeping the
final answer machine-readable lets the notebook render a clean analyst report
while still showing the model's reasoning.
"""

from __future__ import annotations

import json
import re
from typing import Any

# Confidence bands the model must use. Deterministic tool signals should anchor
# these — the model explains *why*, it does not invent severity out of nothing.
CONFIDENCE_RUBRIC = """
Confidence bands (assign per message AND for the overall verdict):
- HIGH   : Multiple corroborating high-severity signals (e.g. DMARC fail + brand
           lookalike link + credential-harvest path). Act now.
- MEDIUM : At least one high-severity signal, or several medium ones, but with
           some ambiguity. Worth an analyst's eyes.
- LOW    : Weak or isolated signals; likely benign but not certain.
- INFO   : No meaningful phishing signals found; treated as benign.
""".strip()

VERDICTS = ["malicious", "likely_phishing", "suspicious", "benign"]

SYSTEM_PROMPT = f"""
You are PhishBowl, a blue-team email triage analyst agent. An SOC analyst gives
you a target mailbox. Your job: investigate the mail that mailbox recently
received and produce a calm, evidence-based triage report with confidence levels.

WORKFLOW (follow in order):
1. Call `sublime_fetch_recent` with the mailbox (and the requested window/limit)
   to list recent messages.
2. For EACH message, call `sublime_get_message` to pull its headers, links, IPs.
3. Run the analysis tools on that message's fields:
   - `analyze_headers` on sender / reply_to / return_path / auth_results / headers
   - `analyze_links` on the links list
   - `analyze_ips` on the ips list
4. Weigh the returned signals to assign a verdict and confidence. Do NOT invent
   signals the tools did not report. If a message has no signals, it is benign.

{CONFIDENCE_RUBRIC}

Verdict must be one of: {", ".join(VERDICTS)}.

OUTPUT: After your investigation, output ONE fenced ```json block and nothing
after it, matching exactly this shape:

```json
{{
  "mailbox": "<the mailbox>",
  "window_minutes": <int>,
  "messages_analyzed": <int>,
  "overall": {{
    "verdict": "<one of the verdicts>",
    "confidence": "<HIGH|MEDIUM|LOW|INFO>",
    "summary": "<2-3 sentence analyst summary>"
  }},
  "findings": [
    {{
      "message_id": "<id>",
      "subject": "<subject>",
      "sender": "<from address>",
      "verdict": "<one of the verdicts>",
      "confidence": "<HIGH|MEDIUM|LOW|INFO>",
      "key_signals": ["<short signal>", "..."],
      "rationale": "<1-2 sentences citing the concrete signals>",
      "recommended_action": "<e.g. quarantine, warn user, no action>"
    }}
  ]
}}
```

Be concise and factual. This is decision-support for a human analyst, not a
final adjudication.
""".strip()


def extract_report(text: str) -> dict[str, Any]:
    """Pull the JSON report out of the model's final message.

    Tries a fenced ```json block first, then the last balanced {...} object.
    Returns {"_parse_error": ..., "raw": text} if nothing parses, so the caller
    can still surface the model's prose.
    """
    if not text:
        return {"_parse_error": "empty response", "raw": ""}

    fenced = re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    for candidate in reversed(fenced):
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue

    # Fall back to the last balanced top-level object in the text.
    obj = _last_json_object(text)
    if obj is not None:
        return obj

    return {"_parse_error": "no JSON object found", "raw": text}


def _last_json_object(text: str) -> dict | None:
    depth = 0
    start = -1
    best = None
    for i, ch in enumerate(text):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start != -1:
                chunk = text[start : i + 1]
                try:
                    best = json.loads(chunk)
                except json.JSONDecodeError:
                    pass
    return best
