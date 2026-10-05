# Submission record

## Repository and branch

- Repository: https://github.com/apeaircreative/my-gecko-buyer
- Submission branch: `main`
- Public MCP endpoint: https://gecko-purchase-check.onrender.com/mcp

## Merged work

- Streamable HTTP MCP transport: https://github.com/apeaircreative/my-gecko-buyer/pull/8
- Public deployment smoke evidence: https://github.com/apeaircreative/my-gecko-buyer/pull/9

## Validation

The final project-04 verification passed locally:

```text
local score: 10/10
```

A remote MCP Streamable HTTP client called `check_purchase` using the
five-beans fixture and received the expected safety refusal:

```json
{
  "passed": false,
  "field": "quantity",
  "asked": 2,
  "found": 1
}
```

## Endpoint behavior

A raw request to `/mcp` returns an MCP JSON-RPC `400` response saying
`Missing session ID`. This is expected: a real MCP Streamable HTTP client
must initialize a session before invoking tools.

## Scope

The deployed service checks unsigned purchase data against a pinned intent.
It does not load a signer, sign a transaction, submit a transaction, or
broadcast a transaction.
