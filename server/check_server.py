"""Keyless MCP server for checking a prepared purchase against a pinned intent."""

from __future__ import annotations

from typing import Any

from mcp.server.mcpserver import MCPServer

from buyer.check import check_all
from buyer.intent import IntentRecord
from buyer.prepared import GeckoRefused, Prepared
from server.guard import is_public_url

server = MCPServer("gecko-purchase-check")


@server.tool()
def check_purchase(
    intent: dict[str, Any],
    prepared_answer: dict[str, Any],
    rpc_url: str | None = None,
) -> dict[str, Any]:
    """Check unsigned purchase bytes against a pinned intent without loading a signer."""
    if rpc_url is not None and not is_public_url(rpc_url):
        return {
            "passed": False,
            "field": "rpc_url",
            "asked": "a public HTTPS URL",
            "found": rpc_url,
        }

    try:
        pinned = IntentRecord(**intent)
        prepared = Prepared.from_answer(prepared_answer)
    except (TypeError, KeyError, ValueError, GeckoRefused) as exc:
        return {
            "passed": False,
            "field": "input",
            "asked": "a valid pinned intent and prepared purchase answer",
            "found": type(exc).__name__,
        }

    verdict = check_all(pinned, prepared)

    if verdict.passed:
        return {
            "passed": True,
            "field": None,
            "asked": None,
            "found": None,
        }

    if verdict.refusal is not None:
        refusal = verdict.refusal
        return {
            "passed": False,
            "field": refusal.field,
            "asked": refusal.asked,
            "found": refusal.found,
        }

    todo = verdict.unwritten
    return {
        "passed": False,
        "field": "not-written",
        "asked": "all purchase checks implemented",
        "found": todo.what if todo is not None else "unknown",
    }


if __name__ == "__main__":
    server.run()
