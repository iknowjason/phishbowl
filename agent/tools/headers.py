"""Header analysis tool.

Turns a message's parsed headers + auth results into a list of concrete signals
an analyst would flag: SPF/DKIM/DMARC failures, From vs Reply-To mismatch,
Return-Path mismatch, and display-name spoofing hints. No model calls — this is
deterministic so the agent's later judgement is auditable.
"""

from __future__ import annotations

import re

from strands import tool


def _domain(address: str) -> str:
    m = re.search(r"@([A-Za-z0-9.\-]+)", address or "")
    return m.group(1).lower().strip(".") if m else ""


@tool
def analyze_headers(
    sender: str,
    reply_to: str = "",
    return_path: str = "",
    auth_results: dict | None = None,
    headers: dict | None = None,
) -> dict:
    """Score a message's headers for spoofing / authentication signals.

    Feed this the fields from ``sublime_get_message``. It returns discrete signals
    (each with a severity) plus the extracted domains, so the agent can weigh
    authentication failures and identity mismatches when assigning confidence.

    Args:
        sender: The From address.
        reply_to: The Reply-To address, if any.
        return_path: The Return-Path / envelope-from, if any.
        auth_results: {"spf","dkim","dmarc"} results (e.g. "pass"/"fail"/"none").
        headers: The full lower-cased header dict (optional, for display-name check).

    Returns:
        {"from_domain", "signals": [{"name","severity","detail"}], "auth_results"}.
        Severity is one of "high", "medium", "low", "info".
    """
    auth_results = {k: str(v).lower() for k, v in (auth_results or {}).items()}
    headers = headers or {}
    signals: list[dict] = []

    from_domain = _domain(sender)
    reply_domain = _domain(reply_to)
    return_domain = _domain(return_path)

    # --- Authentication outcomes ---
    def auth(name: str, weight_fail: str) -> None:
        val = auth_results.get(name, "")
        if val in ("fail", "softfail", "permerror", "temperror"):
            signals.append(
                {"name": f"{name.upper()} {val}", "severity": weight_fail,
                 "detail": f"{name.upper()} authentication returned '{val}'."}
            )
        elif val == "none" or val == "":
            signals.append(
                {"name": f"{name.upper()} none", "severity": "low",
                 "detail": f"No {name.upper()} result present."}
            )

    auth("spf", "medium")
    auth("dkim", "medium")
    auth("dmarc", "high")  # DMARC failure is the strongest single header signal

    # --- Identity mismatches ---
    if reply_domain and from_domain and reply_domain != from_domain:
        signals.append(
            {"name": "Reply-To mismatch", "severity": "high",
             "detail": f"Reply-To domain ({reply_domain}) differs from From ({from_domain})."}
        )
    if return_domain and from_domain and return_domain != from_domain:
        signals.append(
            {"name": "Return-Path mismatch", "severity": "medium",
             "detail": f"Return-Path domain ({return_domain}) differs from From ({from_domain})."}
        )

    # --- Display-name spoofing hint (a brand name in the display but a foreign domain) ---
    display = headers.get("from", "")
    m = re.match(r'\s*"?([^"<]+?)"?\s*<', display)
    if m:
        name_part = m.group(1).strip().lower()
        brandish = re.findall(r"[a-z0-9\-]{3,}", name_part)
        if from_domain and brandish and not any(b in from_domain for b in brandish):
            signals.append(
                {"name": "Display-name vs domain", "severity": "low",
                 "detail": f"Display name '{name_part}' is unrelated to sending domain "
                           f"'{from_domain}'."}
            )

    return {
        "from_domain": from_domain,
        "reply_to_domain": reply_domain,
        "return_path_domain": return_domain,
        "auth_results": auth_results,
        "signals": signals,
    }
