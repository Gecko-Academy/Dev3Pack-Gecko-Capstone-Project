---
name: gecko-buy-on-devnet
description: Use when the student wants their buyer to buy from a store on Solana devnet through Gecko, or a buy is stuck. Triggers on "buy from my store", "run the buyer", "uv run buyer", "prepare_purchase", "sign and submit", "land a purchase", "expires", "blockhash not found", "BlockhashNotFound", "REFUSED on blockhash", "not written yet", or a receipt that did not reconcile. Walks the enforced order (menu, pin, prepare, check, sign, verify, submit, receipt) and explains what each step is asking for. Never signs on mainnet, never writes, prints or moves a key, and never writes the student's checks for them.
allowed-tools: Bash(uv run buyer:*), Bash(uv run pytest:*), Bash(solana balance:*), Read, Grep
---

# Buying on devnet, in the order that makes it safe

A purchase that lands proves the plumbing. A purchase refused by field proves the student.
Your job is to get them to either, and to have them understand which one happened.

## The order, and why each step is where it is

| Step | Who | What it leaves | Why here |
|---|---|---|---|
| signer | `buyer/signer.py` (written) | a loaded devnet key | a cold signer eats the 60-second window |
| menu | `read_menu` (worked example) | `run.menu` | browsing is free and nothing expires: decide here |
| pin | `pin_intent` + `parse_intent` (student) | `intents/<file>.json` | what was asked is on disk before any bytes exist |
| prepare | `prepare` (student) | `run.prepared` | one call, fields FROM THE PIN; starts the clock |
| check | `check` + five checks (student) | a `Verdict` | refuses by field before anything is signed |
| sign | `sign` (student) | signed base64 | the signer re-checks cluster, blockhash and key itself |
| verify | `verify` (student) | Gecko's verdict on the signed bytes | the signed bytes must BE the prepared bytes |
| submit | `submit` (student) | a signature | the only step that changes state |
| receipt | `write_the_receipt` (student) | `receipts/<sig8>.md` | two ledger reads, never the submit answer |

The runner at the bottom of `buyer/agent.py` enforces this order. If a student asks to
reorder it or to skip a step, explain what the step protects instead.

## Do

1. Offline first: `uv run buyer "one espresso" --recorded`. Read the first `[todo]` line
   with the student: it names the file and the function to write next.
2. Explain what that step or check is asking for, point at its docstring and the test in
   `tests/test_your_work.py` that covers it. Let the student write it.
3. When the recorded lane is green (`uv run buyer --cases --recorded`), go live:
   `uv run buyer "one espresso" --devnet`. It needs `scripts/devnet_setup.py` (keys
   outside the repo, funded) and `scripts/create_store.py` (their store).
4. After a landing: open the explorer link, then read `receipts/<sig8>.md` together.

## When it goes wrong

| Output | Meaning | Next |
|---|---|---|
| `[todo] <step> is not written yet` | that TODO is the next thing to write | explain it; do not write it |
| `REFUSED on blockhash` | more than ~60 s between prepare and sign | run again; never re-sign old bytes |
| `REFUSED on cluster` | the RPC is not devnet by genesis hash | fix `GECKO_DEVNET_RPC`; the refusal is correct |
| `Gecko refused, receipt-failed` | the simulation failed | `solana balance -u devnet <buyer>`, and the token balance |
| `the loop's order was broken` | a step did not leave what the next needs | read the message; it names the missing thing |
| receipt `NOT reconciled` | the ledger moved differently from the prepared price | a finding: write it in `docs/ISSUES.md` |

## Will not

- Sign, or suggest signing, on mainnet. Friday's mainnet wallet is the student's own
  (`scripts/mainnet_wallet.py`), capped at 300000 raw per signature, and run only by the
  student; never set one up.
- Create, print, paste, move or commit a key or a keypair file. Keys live in
  `~/.config/dev3pack/`. If a step seems to need a key in the repo, the step is wrong.
- Write `parse_intent`, a check, or a step body for the student, or the expected refusal
  text. Say what it guards and where the test is.
- Retry a submit that did not confirm before reading what it said.
- Claim a purchase landed without a signature and an explorer link from this session.
