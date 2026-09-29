# The defence: Friday 2 October, six minutes

*Your script. Keep the minutes, fill the right-hand column with what YOU will show and
say, and rehearse it once on Thursday against the clock. Delete the italic lines.*

One design rule: everything you show ends in a **receipt** (it landed, and this is what
moved) or a **refusal** (it did not sign, and this is the field that disagreed).

## The six minutes

| Min | On screen | Backed by | What I say |
|---|---|---|---|
| 0:00 | your README's first lines: the sentence and the explorer link | `README.md` | |
| 0:45 | your assistant with Gecko connected: `list_stores` shows *your* store | `docs/connect.md`, `store/store.json` | |
| 1:30 | the live buy: pin, prepare, 7 ticks, sign, verify, submit | `uv run buyer "one espresso" --devnet` | |
| 2:30 | the landing: the explorer, then the receipt with ledger deltas | `receipts/<sig8>.md` | |
| 3:15 | **the injected failure**: the judge draws a card; your buyer refuses and signs nothing | `buyer/check.py`, `refusals/` | |
| 4:30 | tests and the five-case table; one test that was red first | `uv run pytest`, `docs/EVAL_REPORT.md` | |
| 5:15 | the ADR: the decision, and what would reverse it | `docs/adr/0001-refusals-before-signing.md` | |

Friday participants with a registered, funded mainnet wallet may do minute 1:30 on
mainnet against geckocoffee instead (see "Friday on mainnet" below). Everyone else stays
on devnet, and that is the whole defence.

## The four cards

The judge draws one, face down. You do not know which, so you cannot stage it; your
buyer has to refuse it on its own.

| Card | What the judge does | The command | The expected refusal |
|---|---|---|---|
| **Quantity** | asks for two espressos | `uv run buyer "two espressos" --devnet` | `quantity`: asked 2, prepared 1 |
| **Budget** | sets the budget to half the price | `uv run buyer "one espresso" --budget-raw <half> --devnet` | `price_raw`: both numbers |
| **Tampered bytes** | changes one byte of the signed transaction before verify | `uv run buyer "one espresso" --devnet --card tampered` | `signed bytes`: `verify_signed_transaction` refuses, so there is no submit |
| **Stale bytes** | waits past `expires`, then asks you to sign | `uv run buyer "one espresso" --devnet --card stale` | `blockhash`: the bytes expired; prepare again, never re-sign |

Rehearse all four offline first, with no network and no key:

```bash
uv run buyer --cards --recorded      # 4/4 once your steps and checks are written
```

## Before you go on stage

- [ ] One devnet receipt is **committed** (`receipts/<sig8>.md`). If the network fails at
      2:30, show it and say out loud that it is the committed one. Same code path, honest.
- [ ] `uv run buyer --cases --recorded` prints 6/6 and `--cards` prints 4/4.
- [ ] `uv run pytest` is green and `python3 scripts/scan_secrets.py` finds nothing.
- [ ] Your devnet buyer holds SOL and your token (`solana balance -u devnet <buyer>`).
- [ ] Your assistant's connector is live; you tried `list_stores` today, not yesterday.
- [ ] Mainnet only: `uv run python scripts/mainnet_wallet.py show` prints 300000 raw USDC
      and some SOL, and `mainnet-wallet.json` is not in `git status`.

## Friday on mainnet (your own wallet, registered and funded)

The key is made on your machine and never leaves it. Do steps 1 to 5 before Friday.

1. **Make the wallet, on your own machine.**

   ```bash
   uv run python scripts/mainnet_wallet.py create
   ```

   It writes `~/.config/dev3pack/mainnet-wallet.json` (mode 600, outside this repository)
   and prints the public address only. It refuses to overwrite a wallet that exists.

2. **Get a Gecko key**, with the Gecko CLI (published on PyPI as `gecko-surf`; `uvx` runs it
   without installing anything):

   ```bash
   uvx --from gecko-surf gecko login --email <you@example.com>
   ```

   It emails you a one-time code and seals the key in your OS keychain. Where there is no
   keychain (WSL2, a headless Linux box), it shows the key once instead: copy it then.

3. **Tell the instructor the email you logged in with.** Your Gecko account is that email,
   and the instructor grants it to the class. Until then, `register` answers `not-granted`.

4. **Register the wallet's address.** Put the key in `GECKO_API_KEY` without it ever
   appearing on screen, or leave it unset and paste it at the prompt (not echoed):

   ```bash
   export GECKO_API_KEY="$(uvx keyring get gecko:gecko-identity gecko)"
   uv run python scripts/mainnet_wallet.py register
   ```

   It fetches a one-time challenge, signs it with the wallet, and sends the address and the
   signature. The key file never leaves your machine; the Gecko key is never printed. It
   prints `registered <address> for <account>`, or Gecko's reason, word for word.
   Each run uses a fresh one-time challenge; if it fails, fix the reason and run it once
   more (on `rate-limited`, wait a minute first; never loop it). Registering a different
   address **replaces** the old one, which may already be funded: it warns you, stops
   until you pass `--replace`, and either way you tell the instructor.

5. **Wait for funding, then check it.**

   ```bash
   uv run python scripts/mainnet_wallet.py show
   ```

   The founder funds each registered address with 300000 raw USDC (three espressos at
   100000) and about 0.0094 SOL for fees. `show` reads both from a public mainnet RPC and
   signs nothing.

6. **Friday: the buy.**

   ```bash
   uv run buyer "one espresso" --mainnet --store geckocoffee
   ```

   The mainnet lane reads only that wallet, pays in mainnet USDC, and caps every signature
   at `--mainnet-budget-raw 300000` by default. The signer refuses a cap above 300000, any
   purchase above the cap, and any node whose genesis hash is not mainnet's.

**Mainnet is real money.** The budget is the cap, and the balance is the hard one: a
fourth espresso cannot be paid for. Never share the key file, never commit it, never
paste it anywhere (the pre-commit scan refuses `mainnet-*.json`, but that is a seatbelt).
The wallet signs two things only: the registration challenge, and Friday's purchases.
No PayBox, no hosted signer: the key is yours and stays on your machine. Telegram is an
optional extra channel, once a transaction has worked from the terminal.

On stage, run `show` first so the room sees three espressos' worth of USDC, then the buy,
then `show` again: the USDC went down by exactly the price.

## Questions you should be ready for

- Why does Gecko never hold your key, and what would change if it did?
- Which of your seven checks would you drop first, and what risk would you accept?
- Your buyer refused. How does the person at the chat know it was right to?
- What does your receipt NOT prove?
