# Public MCP deployment

## Endpoint

- Service: `gecko-purchase-check`
- Public MCP endpoint: `https://gecko-purchase-check.onrender.com/mcp`
- Platform: Render web service
- Service ID: `srv-db1sumgu01pc73fthm8g`
- Deploy ID: `dep-db1sv07n2mvs739sh850`
- Source branch: `main`
- Start command: `MCP_TRANSPORT=streamable-http uv run python server/check_server.py`

The application receives the hosting platform's `PORT` and exposes the MCP
Streamable HTTP route at `/mcp`.

## Public smoke call

A real MCP Streamable HTTP client connected to:

https://gecko-purchase-check.onrender.com/mcp

It called `check_purchase` using the recorded five-beans fixture, a pinned
intent for two `Beans`, and the recorded one-unit `prepare_purchase` answer.

Observed result:

```text
endpoint: https://gecko-purchase-check.onrender.com/mcp
is_error: False
{
  "passed": false,
  "field": "quantity",
  "asked": 2,
  "found": 1
}
```

This is the expected refusal: the intent requested two bags of Beans, while
the decoded unsigned bytes contain one purchase instruction. The check loads
no signer and does not sign, submit, or broadcast a transaction.

## Raw HTTPS route check

A raw request to the same endpoint returned the expected session-negotiation
response:

```text
HTTP/2 400
x-render-origin-server: uvicorn
{"jsonrpc":"2.0","id":null,"error":{"code":-32600,"message":"Bad Request: Missing session ID"}}
```

That response is expected when `/mcp` is requested without MCP session
initialization; the public client smoke call above performed that initialization.
