---
name: gecko-first-call
description: Use when an agent has to call an API it has never seen and get the call right the first time. Triggers on "add this API to my agent", "integrate this API", "wire up these endpoints", "how do I call this", a first call that came back 404 or 422 or 400, params landing in the wrong place, or an OpenAPI file sitting in the repo that nothing uses yet. Turns an OpenAPI URL or a local spec file into agent tools with the gecko CLI, proves every call offline in recorded mode for zero cost, then wires the tools into this client. Needs no API key, no account and no network when the spec is a local file. Never writes a private key, a keypair file or a seed phrase, and never signs anything.
allowed-tools: Bash(npx:*), Bash(gecko:*), Bash(uv:*), Read, Write
---

# First call, right the first time

Start offline. A call that fails against the schema fails against the API too, and
finding out offline costs nothing.

`gecko` reads an API and produces tools. You do not hand-write a client. If you find
yourself building a request by hand, the comprehension step failed, so fix that instead.

## The command you use

Either of these. The first needs Node and installs nothing.

```bash
npx -y @geckovision/gecko <verb> ...
uv tool install "gecko-surf[serve]" && gecko <verb> ...
```

Quote the brackets. `zsh` treats `[serve]` as a glob and fails before `uv` sees it.
Leave the extra off and `gecko connect` later dies with
`ModuleNotFoundError: No module named 'anyio'`, which names a package nobody typed.

`add`, `test` and `inspect` all accept a local file path. A file on disk always wins
over the URL reading, so nothing leaves the machine.

## Step 1: prove the calls offline

```bash
npx -y @geckovision/gecko test <spec-path-or-url>
```

Real output, from `workflows/specs/receipts.json` in this repo:

```
  [PASS] listReceipts · well_formed — status=200
  [PASS] listReceipts · required_guard — missing 'status' caught
  [PASS] createReceipt · well_formed — status=200
  [PASS] createReceipt · required_guard — missing 'body' caught
  [PASS] getReceipt · well_formed — status=200
  [PASS] getReceipt · required_guard — missing 'receipt_id' caught

6/6 checks passed (recorded mode)
```

Recorded mode builds the response from the spec's own schema. It runs the same code a
live call runs and stops at the transport edge.

Read the tool names in that output before you go on. They are what the agent will pick
from. If a name looks like `get__quote` rather than `getQuote`, the spec has no
`operationId` for that operation, and the agent is picking from a name nobody chose.

Report the counts you actually saw. Do not say "all checks passed" if you did not read
the last line.

## Step 2: wire the tools in

```bash
GECKO_TELEMETRY=off npx -y @geckovision/gecko add <spec-path-or-url> --name <short-name>
```

```
  ✓ comprehended 3 endpoint(s) → first-call-correct tools
  ✓ added to Claude Code (stdio).
```

Tell the developer the endpoint count. It is the first honest signal about whether
gecko found the whole API or one page of it. Three endpoints from a spec with forty is
a finding, not a success.

`add` copies the spec into `~/.gecko/surfaces/<name>.json` and points the MCP server at
the copy. Edit the original afterwards and nothing changes until you run `add` again.

`GECKO_TELEMETRY=off` stops the one anonymous ping `add` sends per new API. Set it and
the whole of step 1 and step 2 run with the network off.

## Step 3: make the call the developer actually wanted

Restart the MCP client so it loads the new server, then ask in plain language. The
agent picks the operation and fills the parameters. Show the developer the request that
went out, not only the answer.

## Going live

`--mode live` on `add`. gecko prompts once for a key, hides the input, and seals it in
the OS keychain. The key never lands in a config file, in shell history, or in a tool
definition the model can read.

gecko refuses to send a key to a host the spec did not come from. When the spec is
published on a different host than the API, say where the API is:
`--base-url https://api.realhost.example`. When you cannot explain why the hosts differ,
stop and ask. That refusal is the only thing standing between a key and a stranger.

## What this skill will not do

- It will not write a key, a keypair file or a seed phrase anywhere, including a
  `.env` you were about to create. Keychain or an environment variable the developer
  sets themselves, nothing else.
- It will not hand-write an HTTP client to work around a comprehension failure.
- It will not run `--mode live` until `gecko test` has passed offline.
- It will not report a command's output it did not run. If a command was not run, say
  which one and why.

## Where to go next

- The API ships no OpenAPI: `gecko-no-spec`.
- You have several candidate APIs and no reason to pick one: `gecko-choose-an-api`.
- It is wired and the call still fails: `gecko-fix-a-call`.
