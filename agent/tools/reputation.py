"""IP analysis tool.

Classifies the sending / first-hop IP addresses: private vs public, reserved
ranges, and (optionally) enrichment from a threat-intel feed if one is wired in.
By default it runs fully offline with structural heuristics; a clearly marked
extension point shows where to plug in GreyNoise / AbuseIPDB / Spamhaus.
"""

from __future__ import annotations

import ipaddress
import os

from strands import tool


def _classify(ip: str) -> tuple[str, str] | None:
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return None
    if addr.is_private:
        return ("info", "Private / internal address (normal for internal relays).")
    if addr.is_loopback:
        return ("low", "Loopback address in the delivery path (unusual).")
    if addr.is_reserved or addr.is_multicast or addr.is_unspecified:
        return ("medium", "Reserved/invalid address in a Received hop (suspicious).")
    if addr.is_link_local:
        return ("medium", "Link-local address in the delivery path (suspicious).")
    return ("info", "Public address — enrich against threat intel for reputation.")


def _enrich(ip: str) -> dict | None:
    """Extension point: return {"severity","detail"} from a reputation feed.

    Left disabled by default so the tool has no external dependencies. To enable,
    set PHISHBOWL_IP_ENRICHMENT=1 and implement a lookup here (e.g. GreyNoise,
    AbuseIPDB, Spamhaus). Keep it fail-open: return None on any error.
    """
    if os.environ.get("PHISHBOWL_IP_ENRICHMENT") != "1":
        return None
    # TODO(operator): call your reputation API here and map the result to a signal.
    return None


@tool
def analyze_ips(ips: list[str]) -> dict:
    """Classify sending / delivery-path IP addresses for suspicious signals.

    Feed this the ``ips`` list from ``sublime_get_message``. It flags reserved or
    malformed addresses in the delivery path and, if enrichment is enabled, adds
    reputation signals. The agent uses these alongside header and link signals.

    Args:
        ips: List of IP address strings from the message's Received path / origin.

    Returns:
        {"evaluated": [...], "signals": [{"name","severity","detail","ip"}]}.
    """
    signals: list[dict] = []
    evaluated: list[str] = []

    for ip in ips or []:
        ip = ip.strip()
        if not ip or ip in evaluated:
            continue
        evaluated.append(ip)

        classified = _classify(ip)
        if classified is None:
            signals.append({"name": "Malformed IP", "severity": "low",
                            "detail": f"'{ip}' is not a valid IP address.", "ip": ip})
            continue
        severity, detail = classified
        if severity != "info":
            signals.append({"name": "IP path anomaly", "severity": severity,
                            "detail": detail, "ip": ip})

        enriched = _enrich(ip)
        if enriched:
            signals.append({**enriched, "ip": ip})

    return {"evaluated": evaluated, "signals": signals}
