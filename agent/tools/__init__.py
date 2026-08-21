"""PhishBowl agent tools.

Two families of tools are exposed to the Strands agent:

* Retrieval tools (`sublime.py`) — pull mail from the Sublime Security tenant.
* Analysis tools (`headers.py`, `links.py`, `reputation.py`) — deterministic
  signal extraction the LLM reasons over to assign a verdict + confidence.

Keeping the analyzers deterministic (plain Python, no model calls) makes the
agent's reasoning auditable: the LLM sees the same structured signals a human
analyst would, and its job is judgement, not parsing.
"""

from .sublime import sublime_fetch_recent, sublime_get_message
from .headers import analyze_headers
from .links import analyze_links
from .reputation import analyze_ips

ALL_TOOLS = [
    sublime_fetch_recent,
    sublime_get_message,
    analyze_headers,
    analyze_links,
    analyze_ips,
]

__all__ = [
    "ALL_TOOLS",
    "sublime_fetch_recent",
    "sublime_get_message",
    "analyze_headers",
    "analyze_links",
    "analyze_ips",
]
