# Project 01: read the menu, prepare, refuse

**Monday 28 September, session 11.** Not marked. About one class.

Keyless. No signing. No money moves. You read a real store on Solana mainnet, ask Gecko
to prepare one purchase, and make it refuse on purpose.

Gecko is how an agent moves money on Solana and proves it landed as asked. Today you do
the first half by hand: read the menu, build the call, read the answer. You stop before
anything is signed.

## What you ship

A folder `projects/01-read-the-menu/responses/` with five files you saved yourself:

| File | What is in it |
|---|---|
| `list_stores.json` | one store's menu, read from its own on-chain account |
| `prepare.json` | what Gecko answered when you asked to buy one product |
| `refusal.json` | a refusal you triggered on purpose |
| `telegram.txt` | the Telegram bot's reply for the same store |
| `notes.md` | four lines in your own words (step 6) |

Then `python3 projects/01-read-the-menu/check.py` prints a local score out of 8.

## Before you start

- This repository, cloned as `my-final-project` (see the root README).
- `curl` and Python 3.11 or newer. On Windows, use Git Bash or WSL2.
- A Solana **public** address to act as the buyer. Your own wallet's address is fine. If
  you have none, make a throwaway one:

  ```bash
  python3 projects/01-read-the-menu/check.py address
  ```

  That prints 32 random bytes written as an address. Nobody holds a key for it, so it
  can never sign and never spend. It is empty on mainnet, and that is useful: you see
  what an empty wallet gets back, which is what most of you will see.

Never paste a private key, a seed phrase or a keypair file anywhere in this project.
Nothing here asks for one. If a step seems to, stop and ask.

```bash
cd my-final-project
mkdir -p projects/01-read-the-menu/responses
```

## The two connectors

Gecko serves two keyless MCP endpoints. They do different jobs.

| Endpoint | What it does |
|---|---|
| `https://mcp.geckovision.tech/gecko/mcp` | lists surfaces and comprehends APIs. 2 tools. It sells nothing |
| `https://mcp.geckovision.tech/orquestra/mcp` | Solana: `list_stores`, `prepare_purchase` and more. 16 tools |

Today's calls all go to **orquestra**. Connect both anyway, so your client sees the whole
picture. Connect only the first and you see a list, but you cannot buy anything.

## Steps

### 1. Connect

Pick **one** of the two ways.

**A. In an MCP client.** Claude Code:

```bash
claude mcp add --transport http gecko https://mcp.geckovision.tech/gecko/mcp
claude mcp add --transport http orquestra https://mcp.geckovision.tech/orquestra/mcp
claude mcp list
```

Claude on the web: Settings, Connectors, add each URL as a custom connector. Any other
MCP client takes the same two URLs. Use the `/gecko/mcp` form, never the bare host: the
bare host answers with a redirect that some clients do not follow.

Then ask the client for each call in steps 2 to 4, and paste the tool's JSON result into
the matching file under `responses/`.

**B. Over curl, with no client at all.** An MCP session is four moves: `initialize`,
read the `mcp-session-id` header it sends back, send `notifications/initialized`, then
`tools/call`. Paste this into your terminal once:

```bash
URL=https://mcp.geckovision.tech/orquestra/mcp
H=$(mktemp)
curl -s -D "$H" -o /dev/null -X POST "$URL" \
  -H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"curl","version":"0"}}}'
SID=$(grep -i '^mcp-session-id:' "$H" | tr -d '\r' | cut -d' ' -f2)
echo "session: $SID"
curl -s -o /dev/null -X POST "$URL" \
  -H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream' \
  -H "mcp-session-id: $SID" \
  -d '{"jsonrpc":"2.0","method":"notifications/initialized"}'

call() {  # usage: call <tool> '<arguments as JSON>'
  curl -s -X POST "$URL" \
    -H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream' \
    -H "mcp-session-id: $SID" \
    -d "{\"jsonrpc\":\"2.0\",\"id\":2,\"method\":\"tools/call\",\"params\":{\"name\":\"$1\",\"arguments\":$2}}"
}
```

`session:` must print a value. If it prints nothing, the first request did not reach the
server; run the block again. A call that answers `Bad Request: Missing session ID` means
the handshake did not run in this terminal. A new terminal means a new handshake.

`check.py` reads the raw curl output as it is, so you never need `jq`. To read a saved
file yourself, `python3 projects/01-read-the-menu/check.py show <file>` prints it as
plain JSON.

### 2. Read the menu

```bash
call list_stores '{"store":"geckocoffee"}' > projects/01-read-the-menu/responses/list_stores.json
python3 projects/01-read-the-menu/check.py show projects/01-read-the-menu/responses/list_stores.json
```

Any store works. Leave out `store` (`call list_stores '{}'`) to see every store on
mainnet, then pick one. In an MCP client, ask: "call list_stores for geckocoffee".

What came back on 2026-09-26, trimmed to the first product:

```json
{
  "program": "BUYuxRfhCMWavaUWxhGtPP3ksKEDZxCD5gzknk3JfAya",
  "stores": [
    {
      "store": "geckocoffee",
      "address": "HVkbYf9PBF49WVViFf7eM1VescsgRHNeu4XJv1XveC8x",
      "authority": "DMjTEZJuV3mpfzBNeeuFy9m47A1bj5CXVhCNVo7BEPzy",
      "fulfilment": {"telegram_channel_id": "@geckocoffeeshop", "set": true},
      "products": [
        {
          "name": "Espresso",
          "price_raw": 100000,
          "decimals": 6,
          "price_ui": "0.1",
          "mint": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
          "mint_note": "USDC",
          "token_program": {
            "address": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
            "name": "classic-spl-token",
            "read": true,
            "recognised": true
          }
        }
      ]
    }
  ],
  "network": "mainnet"
}
```

Pick one product and write down four things: its `name`, `price_raw`, `decimals` and
`mint`. The price in tokens is `price_raw / 10**decimals`. Do that division for display
only. Every comparison uses `price_raw`, a whole number.

**Match on the mint and the token program, never the label.** `mint_note` says "USDC"
for a person to read. Two different mints can wear the same label, and a wallet holding
one cannot pay where the other is priced. The asset is `mint` plus `token_program`.

Also read `fulfilment.set`. `false` means a purchase would be recorded and nobody told to
make it.

### 3. Prepare one purchase

Replace the store, product and buyer with yours. The product name must match the menu
exactly.

```bash
BUYER=<your address from "Before you start">
call prepare_purchase "{\"store\":\"geckocoffee\",\"product\":\"Espresso\",\"buyer\":\"$BUYER\",\"network\":\"mainnet\"}" \
  > projects/01-read-the-menu/responses/prepare.json
python3 projects/01-read-the-menu/check.py show projects/01-read-the-menu/responses/prepare.json
```

Nothing is signed, by you or by Gecko. There are two honest answers, and which one you get
depends on the wallet, not on you.

**The wallet can pay** (it holds the price in that mint plus a little SOL). You get
unsigned bytes and the evidence behind them:

| Field | What it tells you |
|---|---|
| `refused: false`, `status: "pass"` | these exact bytes landed in a simulation against mainnet |
| `effects` | what the transaction would move, read from the bytes and the simulation |
| `expires.blocks_remaining` | how many blocks the bytes stay valid, about 60 seconds' worth |
| `instruction.built_by` | who encoded the instruction |
| `transaction.signed: false` | nobody signed. Gecko holds no key |

The bytes die when `blocks_remaining` runs out. That is fine: you are not signing today.
Re-running the call is free.

**The wallet is empty** (the throwaway address, or a fresh wallet). Gecko refuses
instead of handing you bytes that would fail on chain:

```json
{
  "refused": true,
  "code": "receipt-failed",
  "reason": "the simulation did not pass, so no transaction is returned: a transaction that reverts against observed state would only cost you a fee on chain. Likely cause: the buyer <your address> does not exist on mainnet (0 SOL) — it cannot pay the transaction fee; fund it with SOL first",
  "status": "fail",
  "diagnosis": "the buyer <your address> does not exist on mainnet (0 SOL) ...",
  "accounts": [
    {"account": "receipts", "address": "HVkbYf9PBF49WVViFf7eM1VescsgRHNeu4XJv1XveC8x", "writable": true, "signer": false, "derivation": "PDA(['receipts', store], let_me_buy)"},
    "... one entry per account the purchase touches ..."
  ]
}
```

That is a correct answer. The store and the product resolved, the call was built and
simulated, and the simulation showed the wallet cannot pay the fee. No `expires` and no
bytes come back, because there is nothing worth signing. Read `accounts`: each entry says
how its address was found (`derivation`).

If you get `{"error": ...}` instead, that is the network between you and the node, not an
answer about your order. Run the call again.

### 4. Make it refuse on purpose

Ask for something the store does not sell:

```bash
call prepare_purchase "{\"store\":\"geckocoffee\",\"product\":\"Unicorn latte\",\"buyer\":\"$BUYER\",\"network\":\"mainnet\"}" \
  > projects/01-read-the-menu/responses/refusal.json
python3 projects/01-read-the-menu/check.py show projects/01-read-the-menu/responses/refusal.json
```

You get `refused: true`, `code: "product-unknown"`, a `reason`, and `products`: the real
menu. Gecko does not guess which product you meant. It tells you what exists and lets you
choose.

Another one to try: leave out `buyer`. The code is `signer-required`. It still tells you
the order is valid and names signers that can reach your client.

Copy the `code` and the `reason` into `notes.md`. **A refusal is an answer, not an
error.** It names the rule, and your agent should read it before it tries anything else.

### 5. Compare with the zero-setup path

Open Telegram and message **@gecko_check_bot**:

```
menu for geckocoffee
```

Paste its reply into `projects/01-read-the-menu/responses/telegram.txt`. Compare it with
`list_stores.json`. Same products? Same prices? A person at a chat window reaches the
same engine your curl did, with no setup.

### 6. Write four lines

In `projects/01-read-the-menu/responses/notes.md`:

1. The product you picked, as `price_raw`, `decimals` and `mint`.
2. What `prepare_purchase` answered for your buyer, and why.
3. The refusal `code` and `reason` from step 4.
4. One difference between the Telegram reply and the MCP result, or "none".

### 7. Run the self-check

```bash
python3 projects/01-read-the-menu/check.py
```

Eight named lines, each `PASS` or `FAIL`, then `local score: N/8`. The score is local.
It is not sent anywhere and it does not reach the leaderboard. A `FAIL` line says what
to fix.

## When you are done

- [ ] both connectors added, or the curl handshake printed a session id
- [ ] `list_stores.json` saved, and you can say one product's price as `price_raw` + `decimals` + `mint`
- [ ] `prepare.json` saved, and you can say why it passed or refused
- [ ] `refusal.json` saved, with its `code` and `reason` copied into `notes.md`
- [ ] `telegram.txt` saved and compared
- [ ] `check.py` printed `local score: 8/8`
- [ ] no private key, seed phrase or keypair file anywhere in this repository

## Your turn

Small experiments. Each one teaches one thing.

1. **Filter by product.** `call list_stores '{"product":"water"}'`. Which stores sell
   water? Compare `price_raw` across them. Are they all priced in the same mint?
2. **Watch the clock.** With a wallet that can pay, prepare twice, 30 seconds apart.
   Compare `expires.blocks_remaining` and `expires.blockhash`. Why did they change?
3. **Break the store name.** Ask `prepare_purchase` for a store that does not exist.
   What is the code? Why is it not `product-unknown`?
4. **Name a node without a network.** Add `"rpc_url":"https://api.mainnet-beta.solana.com"`
   and remove `network`. Read the refusal. Why can a hostname not tell Gecko which chain
   it is?
5. **Find a store with no fulfilment.** Call `list_stores` with no filter and look for
   `"set": false`. What would happen to a buyer who paid there?
6. **Break check.py.** Delete a line from `list_stores.json` so it is no longer JSON.
   Run the check. Does the `FAIL` line tell you what is wrong?

## What this project will not do

- Sign anything. No step here signs, and `check.py` fails if a saved transaction says
  `signed: true`.
- Ask for a key. The buyer is a public address. A throwaway one is fine.
- Spend money. Mainnet is read, and simulated against, never written.
