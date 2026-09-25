---
name: gecko-fix-a-call
description: Use when a Gecko-wired call fails and the reason is not obvious. Triggers on "the tool returns fake data", "it says connected but there are no tools", "401 even though I set the key", "404 on an endpoint that exists", "it is refusing to send my key", "ModuleNotFoundError anyio", "Bad Request Missing session ID", "the spec changed and nothing changed", or an inspect run that exited non-zero with a good-looking grade. Sorts the failure into mode, staleness, host pinning, install or transport, then fixes only the one that is actually wrong. Reads no secrets and writes no key, keypair or seed phrase anywhere.
allowed-tools: Bash(npx:*), Bash(gecko:*), Bash(claude:*), Bash(curl:*), Read, Edit
---

# Diagnosing a call that failed

Before you change anything, run the offline check:

```bash
npx -y @geckovision/gecko test <spec-path-or-url>
```

A failure that also reproduces offline is a comprehension problem. A failure that only
happens live is a transport or credential problem. The two have opposite fixes and
guessing which one you have is how an afternoon disappears.

Then take the branch that matches the symptom. One symptom, one cause, one command.

## The answer looks plausible and is not real

The surface is serving recorded mode, which is the default for `gecko add`. Recorded
builds the response from the spec's own schema, so it is well shaped and invented.

```bash
npx -y @geckovision/gecko add <ref> --name <name> --mode live
```

## You edited the spec and nothing changed

`gecko add` copies the spec into `~/.gecko/surfaces/<name>.json` and serves the copy.
The path in the registered command points there, not at your file. Re-run `gecko add`
after every edit to the original.

## The client says connected and loads zero tools

Two causes with opposite fixes, so check them in this order.

1. The client has not reloaded. A running client does not re-read its config. Restart
   it, then `claude mcp list` and look for the check mark.
2. Your shell and your MCP client are in different network namespaces, which happens
   inside sandboxed harnesses. `127.0.0.1` in your terminal is not `127.0.0.1` in the
   client, so a local server curl can reach is invisible to it. The config is already
   correct and rewriting it will not help. Serve behind a real URL with a tunnel, and
   confirm you can fetch that URL from outside your shell before touching the client.

## ModuleNotFoundError: No module named 'anyio'

The install skipped the extra. This is the single most common way to get stuck, and the
traceback names a package you never typed, which sends people searching for anyio.

```bash
uv tool install --force "gecko-surf[serve]"
```

Quote the brackets. `zsh` expands `[serve]` as a glob and the command fails before `uv`
sees it.

## 401 after you set a key

The credential did not resolve. List what the keychain holds:

```bash
gecko auth list
```

It prints names, never values. A name you do not recognise means the key was stored
against a different surface name than the one being called.

## "Refusing to send credentials to that host"

This is working as designed. Gecko will not send a key to a host the OpenAPI document
did not come from, because a spec that names somebody else's server is how a key leaks.

Two readings, and you have to decide which one is true before you act:

- The API publishes its spec on a docs host and serves traffic elsewhere. Say where:
  `gecko add <ref> --base-url https://api.realhost.example --mode live`.
- You cannot explain why the hosts differ. Then `--base-url` is the wrong answer and the
  spec is the problem. Stop and say so.

## Bad Request: Missing session ID

You POSTed to an MCP endpoint without doing the handshake. `initialize` first, read
`mcp-session-id` from the response headers, and send it on every later request. The
endpoint is up; the request was incomplete.

## gecko inspect exited non-zero and the grade looks fine

`inspect` exits non-zero whenever there is a blocking finding, with or without
`--min-grade`. A spec can score 91 out of 100 and still have two blocking findings,
because the letter averages four dimensions and hides the one that matters. Read the
lines marked with a cross.

## What this skill will not do

- It will not run a live call to reproduce a bug before the offline check has run.
- It will not print, log, echo or copy a key, a token, a keypair or a seed phrase, and
  it will not read a file in order to show a secret to a human.
- It will not work around a refusal it cannot explain. A refusal you do not understand
  is a finding to report, not an obstacle to route around.
- It will not claim a fix worked without re-running the command that failed and showing
  the new output.
