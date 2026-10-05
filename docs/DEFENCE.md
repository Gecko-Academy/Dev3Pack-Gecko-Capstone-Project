# The defence: Friday 2 October, six minutes

*Your script. Keep the minutes, fill the right-hand column with what YOU will show and
say, and rehearse it once on Thursday against the clock. Delete the italic lines.*

One design rule: everything you show ends in a **receipt** (it landed, and this is what
moved) or a **refusal** (it did not sign, and this is the field that disagreed).

## The six minutes

| Min | On screen | Backed by | What I say |
|---|---|---|---|
| 0:00 | Project summary and a receipt explorer link | `README.md`, `receipts/5J7qAXeZ.md` | My project is a buyer that checks a purchase before it signs anything. If it matches what I asked for, it creates a receipt showing what moved. If it does not match, it stops and explains why. |
| 0:45 | My store and its menu | `store/store.json`, `docs/connect.md` | This is my devnet store and its products. Reading the menu happens before a purchase is prepared, so I can decide what I want before any transaction is created. |
| 1:30 | A live purchase | `uv run buyer "one AI Interaction Audit" --devnet` | The buyer follows the same order every time: it saves what I asked for, prepares the purchase, checks it, signs only if it matches, checks the signed version, sends it, and saves a receipt. My key stays on my machine. |
| 2:30 | Explorer and receipt | `receipts/4qggqtZF.md`, `receipts/5J7qAXeZ.md` | I do not rely only on the terminal saying it worked. The receipt reads the ledger before and after the purchase. It shows the buyer lost the right amount, the store gained it, and the purchase count went up by one. |
| 3:15 | A safety card | `buyer/check.py`, `refusals/`, `uv run buyer --cards --recorded` | The card can change the quantity, budget, signed bytes, or timing. The buyer should stop on its own. It gives a clear reason, and it does not sign or submit a purchase that fails a check. |
| 4:30 | Smoke tests and fallback | `smoke-report.json`, `smoke-report.recorded.json`, `docs/EVAL_REPORT.md` | The live smoke test was 6/6: one purchase landed and five cases were refused. The recorded smoke test was also 6/6. If the network or hosted service is down, I can use the recorded version instead of trying to debug while presenting. |
| 5:15 | Design choice and limits | `docs/adr/0001-refusals-before-signing.md`, `docs/ISSUES.md` | The main choice in this project is to refuse before signing. I also keep an incident log because a successful code change is not enough if an old report makes it look like the system still fails. This is devnet evidence, not proof that every future request is safe. |

The **finalists** (the students presenting on Friday, named by the instructor) may do
minute 1:30 on mainnet against geckocoffee instead, with a registered, funded wallet (see
"Friday on mainnet" below). Everyone else stays on devnet, and that is the whole defence.

**If the network or Gecko is down on stage,** switch to the recorded answers and say so:
`GECKO_SOURCE=recorded uv run buyer "one espresso" --devnet`. Same code path, replayed.

## The four cards

The judge draws one, face down. You do not know which, so you cannot stage it; your
buyer has to refuse it on its own.

| Card | What the judge does | The command | The expected refusal |
|---|---|---|---|
| **Quantity** | asks for two espressos | `uv run buyer "two espressos" --devnet` | `quantity`: asked 2, prepared 1 |
| **Budget** | sets the budget to half the price | `uv run buyer "one espresso" --budget-raw <half> --devnet` | `price_raw`: both numbers |
| **Tampered bytes** | changes one byte of the signed transaction before verify | `uv run buyer "one espresso" --devnet --card tampered` | `signed bytes`: `verify_signed_transaction` refuses, so there is no submit |
| **Stale bytes** | waits past `expires`, then asks you to sign | `uv run buyer "one espresso" --devnet --card stale` | `blockhash`: the bytes expired; prepare again, never re-sign |

**Stale takes about 40 seconds live:** the runner waits on the chain until the bytes
expire. Say what it is waiting for while it waits. Measured on devnet on 30 September:
quantity and budget 3 s, tampered 8 s, stale 41 s.

Rehearse all four offline first, with no network and no key:

```bash
uv run buyer --cards --recorded                        # 4/4 once your steps and checks are written
uv run buyer "one espresso" --recorded --card tampered # one card at a time
```

## The notebook version

`demo/DEMO_DAY.ipynb` is these six minutes as one cell per beat: your README, `list_stores`,
the live buy, the receipt, the card (set `CARD` to the one drawn), tests, the ADR, and the
mainnet and recorded lanes. Open it with:

```bash
uv run --with jupyter jupyter lab demo/DEMO_DAY.ipynb
```

Run it once on Thursday and keep the outputs: if the network fails on stage, the notebook
that already ran is your fallback, and you say that is what it is.

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

   **Finalists: your instructor sends you a Gecko key privately, already granted.** Skip
   to step 4 and paste it at the prompt (it is not echoed). Otherwise:

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

## The seven questions you will be asked

The same list is on the course's session 15 page. Have each answer ready with a file
attached.

**The evidence**

1. **How do you know it landed?** Not "the terminal said so". The receipt: two ledger
   reads, the deltas, `total_purchases` going from n to n+1, and the explorer link.
2. **What does your receipt not prove?** It proves what moved. It cannot prove that you
   asked for the right thing. Have the limit ready in `docs/ISSUES.md`.
3. **Your buyer refused. How does the person at the chat know it was right to?** The
   refusal names one field and both values, and `refusals/<stamp>-<field>.json` keeps it.

**The design**

4. **Why does Gecko never hold your key, and what would change if it did?** Know where
   your key lives, and which step in `buyer/signer.py` uses it.
5. **Which of your seven checks would you drop first, and what risk would you accept?**
   Answer from `buyer/check.py`, field by field.
6. **What would change your mind about your ADR?** The measurement that would reverse
   it. If nothing would, it was a preference, not a decision.

**The limits**

7. **What breaks it?** You already know one thing. Say it before the card makes it
   obvious.
