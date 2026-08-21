"""Sublime Security retrieval tools.

Wraps the Sublime Platform REST API (https://docs.sublime.security/reference).
Two tools are exposed to the agent:

* ``sublime_fetch_recent`` — list messages a mailbox received in a recent window.
* ``sublime_get_message`` — pull one message's headers, links, and IPs, already
  parsed into a compact structure the analysis tools can chew on.

The API key is read from AWS Secrets Manager at runtime (``SUBLIME_SECRET_ARN``);
for local development you can instead export ``SUBLIME_API_KEY`` directly.
"""

from __future__ import annotations

import email.utils
import functools
import json
import os
import re
from datetime import datetime, timedelta, timezone
from typing import Any

import requests
from strands import tool

# Sublime cloud API base. Self-hosted tenants override this with their own host
# via the SUBLIME_API_BASE env var. Confirm your tenant's base URL in the console
# (Settings ▸ API) — see docs/sublime-setup.md.
DEFAULT_API_BASE = "https://api.platform.sublime.security"

REQUEST_TIMEOUT = 30  # seconds


class SublimeError(RuntimeError):
    """Raised when the Sublime API returns an error or is misconfigured."""


@functools.lru_cache(maxsize=1)
def _api_key() -> str:
    """Resolve the Sublime API key from Secrets Manager, or env for local dev."""
    direct = os.environ.get("SUBLIME_API_KEY")
    if direct:
        return direct.strip()

    secret_id = os.environ.get("SUBLIME_SECRET_ARN") or os.environ.get("SUBLIME_SECRET_NAME")
    if not secret_id:
        raise SublimeError(
            "No Sublime credential found. Set SUBLIME_SECRET_ARN (Secrets Manager) "
            "or SUBLIME_API_KEY (local dev)."
        )

    import boto3  # imported lazily so local/unit use doesn't require AWS

    client = boto3.client("secretsmanager")
    secret = client.get_secret_value(SecretId=secret_id)["SecretString"]
    # Secret may be a raw string or a JSON blob like {"api_key": "..."}.
    try:
        parsed = json.loads(secret)
        if isinstance(parsed, dict):
            return str(parsed.get("api_key") or parsed.get("SUBLIME_API_KEY") or secret).strip()
    except (json.JSONDecodeError, TypeError):
        pass
    return secret.strip()


def _base_url() -> str:
    return os.environ.get("SUBLIME_API_BASE", DEFAULT_API_BASE).rstrip("/")


def _request(method: str, path: str, **kwargs: Any) -> dict:
    url = f"{_base_url()}{path}"
    headers = {
        "Authorization": f"Bearer {_api_key()}",
        "Accept": "application/json",
    }
    headers.update(kwargs.pop("headers", {}))
    try:
        resp = requests.request(method, url, headers=headers, timeout=REQUEST_TIMEOUT, **kwargs)
    except requests.RequestException as exc:  # network / DNS / timeout
        raise SublimeError(f"Sublime API request failed: {exc}") from exc

    if resp.status_code == 401:
        raise SublimeError("Sublime API rejected the key (401). Check the credential.")
    if resp.status_code >= 400:
        raise SublimeError(f"Sublime API {resp.status_code} for {path}: {resp.text[:300]}")
    if not resp.content:
        return {}
    return resp.json()


# --------------------------------------------------------------------------- #
# Tools exposed to the agent
# --------------------------------------------------------------------------- #

@tool
def sublime_fetch_recent(mailbox: str, minutes: int = 5, max_messages: int = 25) -> dict:
    """List the messages a mailbox received recently, newest first.

    Use this first to discover which messages to investigate. It queries Sublime
    for message groups delivered to ``mailbox`` within the last ``minutes`` and
    returns a compact list of message stubs (id, subject, sender, received time).

    Args:
        mailbox: The target user's email address (e.g. "jdoe@corp.example").
        minutes: Look-back window in minutes from now (UTC). Default 5.
        max_messages: Hard cap on messages returned, for cost/latency. Default 25.

    Returns:
        A dict: {"mailbox", "window_minutes", "count", "messages": [ {message_id,
        subject, sender, recipient, received_at}, ... ]}.
    """
    since = (datetime.now(timezone.utc) - timedelta(minutes=max(minutes, 0))).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    params = {
        "mailbox": mailbox,
        "created_at[gte]": since,
        "limit": min(max(max_messages, 1), 500),
    }
    data = _request("GET", "/v0/message-groups", params=params)

    groups = data.get("message_groups") or data.get("results") or data.get("data") or []
    messages: list[dict] = []
    for group in groups:
        for msg in _iter_group_messages(group):
            messages.append(msg)
            if len(messages) >= max_messages:
                break
        if len(messages) >= max_messages:
            break

    return {
        "mailbox": mailbox,
        "window_minutes": minutes,
        "count": len(messages),
        "messages": messages,
    }


@tool
def sublime_get_message(message_id: str) -> dict:
    """Fetch one message and return its headers, links, and IPs, parsed.

    Call this for each message id from ``sublime_fetch_recent`` that warrants a
    closer look. The response is deliberately compact so it can be passed to the
    analysis tools (analyze_headers / analyze_links / analyze_ips).

    Args:
        message_id: The message id from a sublime_fetch_recent stub.

    Returns:
        A dict with: message_id, subject, sender, reply_to, return_path,
        recipient, received_at, auth_results {spf, dkim, dmarc}, headers (dict),
        links (list of url strings), ips (list of ip strings).
    """
    data = _request("GET", f"/v0/messages/{message_id}")
    return _normalize_message(message_id, data)


# --------------------------------------------------------------------------- #
# Normalization helpers (kept resilient to Sublime schema variation)
# --------------------------------------------------------------------------- #

def _iter_group_messages(group: dict) -> list[dict]:
    """Flatten a message group into message stubs."""
    msgs = group.get("messages") or ([group] if group.get("id") else [])
    stubs = []
    for m in msgs:
        data = m.get("data_model") or m.get("message") or m
        stubs.append(
            {
                "message_id": str(m.get("id") or group.get("id") or ""),
                "subject": _dig(data, "subject") or group.get("subject") or "",
                "sender": _sender_address(data),
                "recipient": _first_recipient(data),
                "received_at": m.get("created_at") or group.get("created_at") or "",
            }
        )
    return stubs


def _normalize_message(message_id: str, data: dict) -> dict:
    dm = data.get("data_model") or data.get("message") or data
    headers = _headers_dict(dm)
    return {
        "message_id": message_id,
        "subject": _dig(dm, "subject") or "",
        "sender": _sender_address(dm),
        "reply_to": _address(_dig(dm, "reply_to")) or headers.get("reply-to", ""),
        "return_path": headers.get("return-path", "") or _dig(dm, "return_path") or "",
        "recipient": _first_recipient(dm),
        "received_at": data.get("created_at") or "",
        "auth_results": _auth_results(dm, headers),
        "headers": headers,
        "links": _links(dm),
        "ips": _ips(dm, headers),
    }


def _dig(obj: Any, *path: str) -> Any:
    for key in path:
        if isinstance(obj, dict):
            obj = obj.get(key)
        else:
            return None
    return obj


def _address(obj: Any) -> str:
    if not obj:
        return ""
    if isinstance(obj, str):
        return obj
    if isinstance(obj, dict):
        return str(obj.get("email") or obj.get("address") or obj.get("display_name") or "")
    if isinstance(obj, list) and obj:
        return _address(obj[0])
    return ""


def _sender_address(dm: dict) -> str:
    return (
        _address(_dig(dm, "sender"))
        or _address(_dig(dm, "from"))
        or _address(_dig(dm, "headers", "from"))
    )


def _first_recipient(dm: dict) -> str:
    for key in ("recipients", "to"):
        val = _dig(dm, key)
        if isinstance(val, dict):
            val = val.get("to") or val.get("recipients")
        if isinstance(val, list) and val:
            return _address(val[0])
        if val:
            return _address(val)
    return ""


def _headers_dict(dm: dict) -> dict:
    raw = _dig(dm, "headers")
    out: dict[str, str] = {}
    if isinstance(raw, dict):
        for k, v in raw.items():
            out[k.lower()] = v if isinstance(v, str) else json.dumps(v)
    elif isinstance(raw, list):
        # list of {name, value}
        for h in raw:
            name = str(h.get("name", "")).lower()
            if name:
                out[name] = str(h.get("value", ""))
    return out


def _auth_results(dm: dict, headers: dict) -> dict:
    # Prefer Sublime's parsed auth block; fall back to Authentication-Results header.
    parsed = _dig(dm, "authentication_results") or _dig(dm, "auth_summary") or {}
    result = {"spf": "", "dkim": "", "dmarc": ""}
    if isinstance(parsed, dict):
        for key in result:
            v = parsed.get(key)
            if isinstance(v, dict):
                v = v.get("result") or v.get("value")
            if v:
                result[key] = str(v).lower()
    ar = headers.get("authentication-results", "")
    for key in result:
        if not result[key]:
            m = re.search(rf"\b{key}=(\w+)", ar, re.IGNORECASE)
            if m:
                result[key] = m.group(1).lower()
    return result


def _links(dm: dict) -> list[str]:
    urls: list[str] = []
    for link in _dig(dm, "links") or []:
        if isinstance(link, dict):
            u = link.get("href") or link.get("url") or link.get("display_url")
        else:
            u = link
        if u:
            urls.append(str(u))
    # Fall back to scraping the body if no structured links are present.
    if not urls:
        body = _dig(dm, "body", "plain", "raw") or _dig(dm, "body", "html", "raw") or ""
        urls = re.findall(r"https?://[^\s\"'<>)]+", str(body))
    # De-dupe, preserve order.
    seen: set[str] = set()
    return [u for u in urls if not (u in seen or seen.add(u))]


def _ips(dm: dict, headers: dict) -> list[str]:
    ips: list[str] = []
    origin = _dig(dm, "sender_ip") or _dig(dm, "origin", "ip") or _dig(dm, "ip_address")
    if origin:
        ips.append(str(origin))
    # Pull IPs out of Received: headers (first hop is usually the origin).
    received = headers.get("received", "")
    ips += re.findall(r"\[?(\d{1,3}(?:\.\d{1,3}){3})\]?", received)
    seen: set[str] = set()
    return [ip for ip in ips if not (ip in seen or seen.add(ip))]
