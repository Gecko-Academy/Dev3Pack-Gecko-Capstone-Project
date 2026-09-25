---
name: gecko-solana-read
description: Use when reading Solana state or preparing a Solana call through Gecko without signing anything. Triggers on "browse the stores", "what does this store sell", "what does this program cost", "prepare a purchase", "derive this PDA", "what accounts does this instruction need", or "check this transaction before it counts". Uses the keyless orquestra endpoint, where every path ends in unsigned bytes plus a receipt. This skill never signs, never broadcasts, never sets up a wallet and never touches a private key, a keypair file or a seed phrase. If a task needs a signature, it stops and hands the bytes back.
allowed-tools: Bash(claude:*), Bash(curl:*), Read
---

# Reading Solana without a key

The boundary first, because it is the whole skill. You produce unsigned bytes and a
receipt. Signing happens in a wallet the developer controls, outside this repository.
When a task needs a signature you stop, hand back the bytes, and say what they would do.

The endpoint is `https://mcp.geckovision.tech/orquestra/mcp`. No key, no account,
16 tools. Wire it with `gecko-connect-mcp`.

## The order, and the order matters

**1. Browse.** `list_stores` for storefronts, `find_start` for any other program
("buy this token on pump and hold it" returns the program, the instruction, and the
derive plan in dependency order). Reading is free and nothing expires. Do all the
deciding here.

**2. Prepare, once, and only after the buyer has chosen.** `prepare_purchase` returns
unsigned bytes carrying a live blockhash, and those bytes expire with it in about a
minute. Preparing three options to compare them burns the window on all three. Re-running
is free, so prepare late.

**3. Stop.** Hand over the bytes and the receipt.

## What to read before you trust anything

`list_stores` is a menu, not an authorisation. It reports what the accounts say.

**Match on the mint address, never the symbol.** The endpoint returns a `mint_note`, and
that is a human label. Two different mints can wear the same one. A token-2022 mint and
a classic SPL mint called the same thing are different assets, and a wallet holding one
cannot pay where the other is priced. Compare `mint` and `token_program`.
`token_program.read: false` means the mint could not be read, which is not the same as
classic.

**Check `fulfilment.set`.** `false` means a purchase would be recorded on chain and
nobody would be told to make it. Say that out loud before anyone pays. The money moves
and the order never arrives, and nothing on chain shows it.

**`read_accounts` proves what it returns.** Seed values are decoded at offsets from the
IDL and derived back to the address they came from. Anything it lists under `unverified`
failed that check. Read those, never use them. A discriminator match alone proves
nothing, because anyone can create a real account of a declared type with themselves as
admin.

## try_purchase, and what it actually does

`try_purchase` is a rehearsal on a local fork of mainnet. It funds a throwaway buyer
with cheatcodes, signs, lands, and then reads the chain back to show what moved. It does
sign, with a key created inside the call and thrown away when it returns, and it cannot
reach mainnet. Use it to see the effect. It is not a substitute for reading the
prepared bytes.

## Refusals are the product

Gecko refuses instead of guessing, and every refusal names its own next step. Read it
before improvising. A refusal naming an unknown store means that store is absent; it
never means pick a different one. Quote the refusal to the developer verbatim.

## What this skill will not do

- It will not sign a transaction, in any mode, for any reason.
- It will not call `submit_transaction`. That tool exists on this endpoint and it
  broadcasts already-signed bytes. This skill produces nothing signed, so it has nothing
  to give it.
- It will not set up a wallet, add a signer connector, generate a keypair, read a
  keypair file, or ask anyone to paste a private key or a seed phrase.
- It will not ask a human to type a public key either. Call the tool without `buyer` and
  the refusal names the signers that can reach this client.
- It will not report a balance, a price or an address it did not read from a tool
  response in this session. If a read failed, say the read failed.
