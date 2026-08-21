"""Link & domain analysis tool.

Extracts registrable domains from a message's URLs and flags the classic phishing
tells: raw-IP URLs, punycode / homoglyph lookalikes of well-known brands, URL
shorteners, credential-harvest paths, and open-redirect chains. Deterministic and
offline — no DNS or reputation calls — so it is safe to run on suspicious mail.
"""

from __future__ import annotations

import re
from urllib.parse import urlparse, parse_qs

from strands import tool

SHORTENERS = {
    "bit.ly", "tinyurl.com", "t.co", "goo.gl", "ow.ly", "buff.ly", "is.gd",
    "cutt.ly", "rebrand.ly", "rb.gy", "shorturl.at", "lnkd.in",
}

# Brands frequently impersonated in credential phishing. Used only for
# lookalike detection, never as an allowlist.
BRAND_TOKENS = {
    "microsoft", "office365", "outlook", "onedrive", "sharepoint", "google",
    "gmail", "apple", "icloud", "amazon", "paypal", "docusign", "adobe",
    "okta", "netflix", "facebook", "instagram", "linkedin", "chase", "wellsfargo",
}

CRED_PATH_HINTS = ("login", "signin", "sign-in", "verify", "secure", "account",
                   "update", "password", "auth", "mfa", "webmail", "portal")

IP_URL = re.compile(r"^https?://\d{1,3}(?:\.\d{1,3}){3}(?::\d+)?(?:/|$)")


def _registrable_domain(host: str) -> str:
    parts = host.lower().split(".")
    return ".".join(parts[-2:]) if len(parts) >= 2 else host.lower()


def _levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


@tool
def analyze_links(urls: list[str]) -> dict:
    """Flag suspicious URLs, domains, and lookalikes in a message.

    Feed this the ``links`` list from ``sublime_get_message``. It returns the set
    of distinct domains plus per-URL signals so the agent can judge whether the
    message is steering the user to a hostile or impersonating destination.

    Args:
        urls: List of URL strings extracted from the message.

    Returns:
        {"domains": [...], "signals": [{"name","severity","detail","url"}],
         "url_count"}. Severity is "high", "medium", "low", or "info".
    """
    signals: list[dict] = []
    domains: list[str] = []

    for url in urls or []:
        try:
            parsed = urlparse(url)
        except ValueError:
            continue
        host = (parsed.hostname or "").lower()
        if not host:
            continue
        reg = _registrable_domain(host)
        if reg not in domains:
            domains.append(reg)

        # Raw-IP URL — legitimate mail almost never links to a bare IP.
        if IP_URL.match(url):
            signals.append({"name": "Raw-IP URL", "severity": "high",
                            "detail": f"Link points at a bare IP address: {host}.", "url": url})

        # Punycode / IDN homograph.
        if "xn--" in host:
            signals.append({"name": "Punycode domain", "severity": "high",
                            "detail": f"Internationalized (punycode) domain: {host}.", "url": url})

        # Brand lookalike (edit-distance 1–2 from a known brand token).
        label = reg.split(".")[0]
        for brand in BRAND_TOKENS:
            if label != brand and 0 < _levenshtein(label, brand) <= 2:
                signals.append({"name": "Brand lookalike", "severity": "high",
                                "detail": f"Domain label '{label}' resembles '{brand}'.",
                                "url": url})
                break

        # URL shortener — hides the true destination.
        if reg in SHORTENERS:
            signals.append({"name": "URL shortener", "severity": "medium",
                            "detail": f"Shortened link ({reg}) hides its destination.", "url": url})

        # Credential-harvest path hints.
        path_q = (parsed.path + "?" + parsed.query).lower()
        if any(h in path_q for h in CRED_PATH_HINTS):
            signals.append({"name": "Credential-harvest path", "severity": "low",
                            "detail": f"Path suggests a login/verify page: {parsed.path}.",
                            "url": url})

        # Open-redirect chain (a full URL sitting in a query parameter).
        for values in parse_qs(parsed.query).values():
            if any(re.search(r"https?%3a|https?://", v, re.IGNORECASE) for v in values):
                signals.append({"name": "Nested redirect", "severity": "medium",
                                "detail": "A second URL is embedded in the query string "
                                          "(possible open redirect).", "url": url})
                break

    return {"domains": domains, "url_count": len(urls or []), "signals": signals}
