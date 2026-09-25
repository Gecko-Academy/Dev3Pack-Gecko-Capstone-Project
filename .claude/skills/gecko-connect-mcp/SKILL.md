---
name: gecko-connect-mcp
description: Use when wiring a Gecko MCP endpoint into this client and proving it answers. Triggers on "connect gecko", "add the gecko MCP server", "set up the hosted surface", "how do I use orquestra", an mcp.json that needs an entry, or a client that reports Connected and then loads zero tools. Covers the two keyless hosted endpoints, a local serve of your own spec, and the loopback problem that makes a local server invisible to a sandboxed client. Ends with one read-only call that returned real data, never with a config edit nobody tested. Puts no key in any config file and signs nothing.
allowed-tools: Bash(claude:*), Bash(npx:*), Bash(gecko:*), Bash(curl:*), Read, Edit
---

# Connecting Gecko over MCP

A config edit is not the job. A tool that answered is the job.

## Step 1: pick local or hosted

The question that decides it is whose key the API needs.

- The API needs the developer's own key: serve it **locally**. Gecko never holds a key
  and a per-person key cannot live on a shared endpoint.
- The API is public: use a **hosted** endpoint. No key, no account.

Two hosted endpoints are keyless today, and their tool lists were read from them rather
than copied from a page:

| Endpoint | Tools |
|---|---|
| `https://mcp.geckovision.tech/gecko/mcp` | 2: `list_surfaces`, `comprehend_api` |
| `https://mcp.geckovision.tech/orquestra/mcp` | 16, Solana, read and prepare |

`list_surfaces` returns the other mounts and their own URLs. That root endpoint only
comprehends and lists, so to use a surface you reconnect to the URL it gives you.
Read it live rather than writing the mounts into a file; the list moves.

## Step 2: wire it

Claude Code:

```bash
claude mcp add --transport http gecko https://mcp.geckovision.tech/gecko/mcp
```

```
Added HTTP MCP server gecko with URL: https://mcp.geckovision.tech/gecko/mcp to local config
```

`-s user` puts it in the user scope instead of this project. Other clients take the
same URL in their own JSON: Cursor in `~/.cursor/mcp.json`, VS Code in
`.vscode/mcp.json`, and Claude on the web accepts the URL with no JSON at all.

For your own spec, served locally:

```bash
npx -y @geckovision/gecko add <spec-path> --name <short-name>
```

That comprehends the spec and registers a stdio server in one step. It copies the spec
into `~/.gecko/surfaces/<name>.json` and serves the copy, so re-run it after you edit
the original.

## Step 3: prove it answers

```bash
claude mcp list
```

```
gecko: https://mcp.geckovision.tech/gecko/mcp (HTTP) - ✔ Connected
```

Connected is not enough. Call one read-only tool and show the developer what came back.
`list_surfaces` on the gecko endpoint, `list_stores` on orquestra. If the client has not
picked the server up yet, restart it; a running client does not reload its config.

For a gated hosted surface there is a one-line check that does the whole round trip:

```bash
gecko connect <surface> --probe
```

```
  ✓ connected to jupiter 0.11.0 — 7 tools. The key resolved, the host was reached, and auth passed.
```

Without `--probe`, `gecko connect` serves over stdio and waits for a client. Sitting
there silently is the correct behaviour, not a hang.

## Connected, and zero tools

Two causes, and they have opposite fixes.

**The client did not reload.** Restart it. Check first.

**Your shell and your MCP client are in different network namespaces.** This happens
inside sandboxed agent harnesses. `127.0.0.1` in your terminal is not `127.0.0.1` in the
client, so a local server that curl reaches is invisible to the client. Rewriting the
config will not help, because the config is already right. Put the server behind a real
URL: run a tunnel, then serve with `--public-url` set to the tunnel's address. Confirm
by fetching that URL from outside your shell before touching the client again.

## What this skill will not do

- It will not declare success on a config edit. If no tool call returned data, say the
  wiring is unverified and say which step stopped.
- It will not put an API key, a token or a header value into `mcp.json`, `.claude.json`,
  or any other file in the repo. Keys live in the OS keychain.
- It will not sign or broadcast anything.
- It will not paste a list of hosted surfaces from memory. Call `list_surfaces`.
