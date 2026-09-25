---
name: gecko-choose-an-api
description: Use when the agent has a goal but no service picked yet, or when several candidate APIs are on the table and something has to choose between them. Triggers on "find me an API that does X", "which of these should I use", "is this API any good", "why does the agent keep getting this call wrong", "what does this cost", or a goal stated with no endpoint attached. Reads the live surface list instead of a hardcoded one, grades each candidate offline with gecko inspect for zero cost, and reports a pick with the evidence behind it. Never spends money, never enters payment details, never holds a key and never signs.
allowed-tools: Bash(npx:*), Bash(gecko:*), Bash(curl:*), Read, Write
---

# Choosing the service

The goal arrives without an endpoint. Your job is to end with one named service, the
reason it was picked, and the evidence a reader can re-run.

The rule that governs everything below: **a claim you cannot back is worse than a
missing answer.** "This API supports pagination" with nothing behind it costs the
developer an hour when it turns out false. "I could not find pagination in the spec"
costs them a minute. Write the second one.

## Step 1: find candidates

Read the catalogue live. Do not use a list of services written into any file in this
repo, including this one, because the catalogue changes and a stale list sends the
agent at something that moved.

The keyless surface list lives at `https://mcp.geckovision.tech/gecko/mcp` and answers
two tools, `list_surfaces` and `comprehend_api`. If this client already has that server
connected, call `list_surfaces` as a tool. If not, either run `gecko-connect-mcp` first
or use the two-step HTTP handshake, which needs a session id from the `initialize`
response:

```bash
URL=https://mcp.geckovision.tech/gecko/mcp
H=$(mktemp)
curl -s -D "$H" -o /dev/null -X POST "$URL" \
  -H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"curl","version":"0"}}}'
SID=$(grep -i '^mcp-session-id:' "$H" | tr -d '\r' | cut -d' ' -f2)
curl -s -X POST "$URL" -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' -H "mcp-session-id: $SID" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"list_surfaces","arguments":{}}}'
```

A single POST without the session id comes back `Bad Request: Missing session ID`. That
is the handshake missing, not the endpoint being down.

Candidates can also come from anywhere else: a spec URL the developer pasted, a docs
site, an OpenAPI file already in the repo.

## Step 2: grade each candidate, offline

```bash
npx -y @geckovision/gecko inspect <spec-path-or-url>
```

Free, no key, no call to the API. Run it on every candidate before you argue for one.
`workflows/survey.py` in this repo does that fan-out for you over several candidates at
once.

**Read the findings, not the letter.** Measured on `workflows/specs/quotes.json`:

```
  specs-quotes-json: agent-readiness A (91/100) — 2 blocking, 2 warnings
  hygiene               56/100
      ✗ [GET /quote] no operationId
         → add a unique operationId — it becomes the agent's tool name
```

Grade A, and two blocking findings. The letter averages four dimensions and the average
hides the one that will bite. `inspect` exits non-zero whenever there is a blocking
finding, with or without `--min-grade`, so the exit code is more honest than the letter.

What the common findings mean for a caller:

- no `operationId`: the agent picks a tool named `get__quote`, so intent matching gets
  worse the more operations the API has.
- no summary or description: nothing for the agent to match a request against.
- an undeclared enum: the agent invents a plausible value and the API rejects it.
- a missing required marker: the agent leaves out a field the API demands.

## Step 3: the cost question

If money is involved, find out how much and say so before anything is called. Look for a
pricing page, a `402` response documented in the spec, or an `x-` extension naming a
price. When you cannot find it, say you could not find it.

You do not spend. You do not enter card details, connect a wallet, hold a key or sign
anything. You bring the developer a price and a named service, and they decide.

## Step 4: report

One pick. One paragraph of why. Then a table of every candidate with its grade, its
blocking count, and its `gecko test` result, so the reader can disagree with you using
the same numbers. Name what you could not check, separately, so it does not read as
something you checked.

## What this skill will not do

- It will not recommend a service it did not run `gecko inspect` against.
- It will not state a capability it did not see in the spec or the docs. Missing is a
  finding; invented is a defect.
- It will not spend money, enter payment details, connect a wallet, or sign.
- It will not treat a grade as a verdict on the service. A grade is about the spec, and
  a spec is a claim about an API rather than the API. A well-described API can still be
  down.
