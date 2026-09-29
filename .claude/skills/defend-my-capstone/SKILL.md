---
name: defend-my-capstone
description: Use when the student is preparing the Friday 2 October presentation. Triggers on "Friday", "defence", "defense", "presentation", "demo", "rehearse", "six minutes", "the cards", "injected failure", "what will the judge ask". Walks the six minutes in docs/DEFENCE.md, checks that a devnet receipt is committed before going on stage, and runs the four failure cards (quantity, budget, tampered bytes, stale bytes) against the buyer, recorded first. Never fakes a landing, never commits a key, never signs on mainnet unless the student made, registered and funded their own capped wallet (scripts/mainnet_wallet.py) and runs it themselves.
allowed-tools: Read, Grep, Bash(uv run buyer:*), Bash(uv run pytest:*), Bash(python3 scripts/scan_secrets.py:*), Bash(git status:*), Bash(git log:*)
---

# Defending the capstone

Six minutes, one judge, one card drawn face down. Everything shown ends in a receipt or a
refusal.

## 1. Readiness, before anything else

Run these and report what each printed, not what it should print:

```bash
python3 scripts/scan_secrets.py          # nothing found
uv run pytest                            # green
uv run buyer --cases --recorded          # 6/6
uv run buyer --cards --recorded          # 4/4
ls receipts/*.md                         # at least one devnet receipt, committed
git status --short receipts/             # nothing uncommitted there
```

If a receipt is not committed, say so first: it is the fallback if the network fails at
minute 2:30, and it must be said out loud if used.

## 2. The six minutes

Walk `docs/DEFENCE.md` minute by minute. For each, ask the student what they will say and
check it points at a file that exists: README sentence and explorer link (0:00), the
connector and `list_stores` showing their store (0:45), the live buy (1:30), the receipt
(2:30), the card (3:15), tests and the five-case table (4:30), the ADR (5:15). Time one
full run. Say which minute ran long.

## 3. The four cards

Run each against the buyer, recorded first, then on devnet if the student wants:

| Card | Command | Must end |
|---|---|---|
| quantity | `uv run buyer "two espressos" --devnet` | `REFUSED on quantity: asked 2, prepared 1` |
| budget | `uv run buyer "one espresso" --budget-raw <half> --devnet` | `REFUSED on price_raw`, both numbers |
| tampered bytes | `uv run buyer "one espresso" --devnet --card tampered` | `REFUSED on signed bytes`, nothing submitted |
| stale bytes | `uv run buyer "one espresso" --devnet --card stale` | `REFUSED on blockhash`, nothing signed |

For each, ask the student to explain which line of their code refused, and what would have
happened without it.

## 4. The questions

Ask them the four at the end of `docs/DEFENCE.md`, and the one from their ADR: what would
reverse the decision? A good answer names an observation, not an opinion.

## Will not

- Stage a card, or hard-code a refusal so a card passes. The judge picks; the code decides.
- Present a recorded run as a live one. If the committed receipt is shown, it is said.
- Create, handle or commit any key. Friday's mainnet wallet is the student's own, made
  with `scripts/mainnet_wallet.py create`, funded with three espressos, capped at 300000
  raw per signature, and run by the student themselves; never set one up or sign with one.
- Write the student's ADR, script or answers. Ask; do not author.
