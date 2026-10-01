"""The buyer's loop: signer, menu, pin, prepare, check, sign, verify, submit, receipt.

The STEP BODIES are yours (projects 02 and 03); `read_menu` is written as the worked
example. The RUNNER at the bottom is not yours to change: it calls the steps in this
order and checks, after each one, that it left what the next one needs. That is how the
order is enforced. A step that skips ahead, prepares before a pin is on disk, or signs
without a passing check is stopped by the runner, not by good intentions.

Every step reads and writes the `Run`. Nothing is global.
"""

from __future__ import annotations

import base64
import json
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .chain import ChainError
from .check import FieldResult, NotYetWritten, Refused, Verdict, check_all
from .intent import Context, IntentRecord, Menu, parse_intent, pin, read_pin, slug
from .ledger import Chain
from .mcp_client import Gecko, GeckoUnavailable
from .prepared import GeckoRefused, Prepared
from .receipt import Receipt, Snapshot, read_snapshot, reconcile
from .receipt import write as write_receipt
from .signer import Signer


@dataclass
class Run:
    ask: str
    context: Context
    gecko: Gecko
    chain: Chain
    signer: Signer
    #: where intents/, receipts/ and refusals/ are written
    out: Path
    source: str = "devnet"
    card: str | None = None
    menu: Menu | None = None
    intent: IntentRecord | None = None
    intent_path: Path | None = None
    answer: dict[str, Any] | None = None
    prepared: Prepared | None = None
    verdict: Verdict | None = None
    before: Snapshot | None = None
    signed: str | None = None
    verified: dict[str, Any] | None = None
    submitted: dict[str, Any] | None = None
    receipt: Receipt | None = None


# ==========================================================================================
# The steps. Each one does ONE thing and leaves its result on the run.
# ==========================================================================================


def read_menu(run: Run) -> None:
    """Worked example: read the store's menu from its own on-chain account, through Gecko.

    Browsing is free and nothing expires, so every decision is made here, before any bytes.
    """
    answer = run.gecko.call(
        "list_stores", {"store": run.context.store, "network": run.context.network}
    )
    run.menu = Menu.from_list_stores(answer, run.context.store)


def pin_intent(run: Run) -> None:
    """
    PIN THE USER'S REQUEST BEFORE ANY PURCHASE BYTES EXIST.

    ASK
      ↓
    parse_intent()
      ↓
    IntentRecord = "what we understood the user to ask for"
      ↓
    pin to disk
      ↓
    PREPARE

    Defense boundary:
    The pin becomes the frozen reference for every later check.
    Prepared purchase data must never be used to create the pin.

    If the request cannot be parsed, let the existing refusal
    propagate to the runner.
    """
    if run.menu is None:
        raise OrderBroken("read_menu left no menu")
    run.intent = parse_intent(run.ask, run.menu, run.context)
    run.intent_path = pin(run.intent, run.out / "intents")


def prepare(run: Run) -> None:
    """
    PREPARE THE PURCHASE FROM THE PIN.

    PIN
      ↓
    prepare_purchase()
      ↓
    raw answer
      ↓
    Prepared

    Defense boundary:
    The purchase request comes from run.intent, not directly
    from the user's ask or other mutable context.

    This step prepares unsigned bytes.
    It does not sign or approve the purchase.
    """
    if run.intent is None:
        raise OrderBroken("prepare requires a pinned intent")

    run.answer = run.gecko.call(
        "prepare_purchase",
        {
            "store": run.intent.store,
            "product": run.intent.product,
            "buyer": run.intent.buyer,
            "network": run.intent.network,
        },
    )
    run.prepared = Prepared.from_answer(run.answer)


def check(run: Run) -> None:
    """
    COMPARE THE PREPARED PURCHASE AGAINST THE PIN.

    PIN
      ↓
    run.intent
      ↓
    check_all()
      ↑
    run.prepared
      ↓
    VERDICT
      ├── agree → continue
      ├── refusal → runner refuses
      └── not-written → runner stops

    This step only evaluates the prepared purchase.
    It does not sign, modify, or send anything.
    """
    run.verdict = check_all(run.intent, run.prepared)


def sign(run: Run) -> None:
    """TODO (project 03): have the signer sign the exact prepared bytes, once.

    `run.signer.sign(run.prepared)` returns the signed base64. Leave it on `run.signed`.
    The signer refuses by itself if the cluster, the budget or the blockhash is wrong.
    """
    raise NotYetWritten("sign", "buyer/agent.py: sign the prepared bytes with run.signer")


def verify(run: Run) -> None:
    """TODO (project 03): ask Gecko whether the signed bytes ARE the bytes it prepared.

    Call `verify_signed_transaction` with the signed transaction, the `binding` and
    `binding_strength` from the prepared answer, `last_valid_block_height`, and
    `rpc_url = run.chain.rpc_url`. Leave the answer on `run.verified`.
    """
    raise NotYetWritten("verify", "buyer/agent.py: call verify_signed_transaction")


def submit(run: Run) -> None:
    """TODO (project 03): send the verified bytes, through Gecko, to the signer's own RPC.

    Call `submit_transaction` with the signed transaction, the `binding`,
    `last_valid_block_height` and `rpc_url = run.chain.rpc_url`. Leave the answer on
    `run.submitted`. Never call it twice for the same bytes: if it did not confirm, read
    what it said first.
    """
    raise NotYetWritten("submit", "buyer/agent.py: call submit_transaction")


def write_the_receipt(run: Run) -> None:
    """TODO (project 03): read the ledger again and reconcile it with the first read.

    `read_snapshot(...)` for the after-read, then `reconcile(...)` with `run.before`, and
    leave the `Receipt` on `run.receipt`. The runner writes it to `receipts/`.
    """
    raise NotYetWritten("write_the_receipt", "buyer/agent.py: read the ledger and reconcile")


# ==========================================================================================
# The runner. Not yours to change: it is what makes the order a fact.
# ==========================================================================================


class OrderBroken(RuntimeError):
    """A step did not leave what the next one needs, or did something out of turn."""


@dataclass
class Outcome:
    ask: str
    #: landed | refused | gecko-refused | not-written | order-broken | unavailable
    kind: str
    step: str
    refusal: FieldResult | None = None
    gecko_code: str | None = None
    detail: str = ""
    receipt: Receipt | None = None
    intent_path: str | None = None
    record_path: str | None = None
    checks: list[str] = field(default_factory=list)
    signed: bool = False

    def to_json(self) -> dict[str, Any]:
        out = asdict(self)
        out["refusal"] = asdict(self.refusal) if self.refusal else None
        return out


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _short(path: Path | str, root: Path) -> str:
    try:
        return str(Path(path).resolve().relative_to(Path(root).resolve()))
    except ValueError:
        return str(path)


def _tamper(signed_b64: str) -> str:
    """The judge's card: one byte of the signed message changed after signing."""
    raw = bytearray(base64.b64decode(signed_b64))
    raw[-1] ^= 0x01
    return base64.b64encode(bytes(raw)).decode()


def _write_refusal(run: Run, outcome: Outcome) -> Path:
    directory = run.out / "refusals"
    directory.mkdir(parents=True, exist_ok=True)
    name = outcome.refusal.field if outcome.refusal else (outcome.gecko_code or outcome.kind)
    stamp = _now().replace(":", "").replace("-", "")[:22]
    path = directory / f"{stamp}-{slug(name)}.json"
    body = {
        "ask": run.ask,
        "step": outcome.step,
        "field": outcome.refusal.field if outcome.refusal else f"gecko:{outcome.gecko_code}",
        "asked": outcome.refusal.asked if outcome.refusal else None,
        "found": outcome.refusal.found if outcome.refusal else None,
        "where": outcome.refusal.where if outcome.refusal else "gecko",
        "note": outcome.refusal.note if outcome.refusal else outcome.detail,
        "signed": outcome.signed,
        "intent": _short(run.intent_path, run.out) if run.intent_path else None,
        "source": run.source,
        "at": _now(),
    }
    path.write_text(json.dumps(body, indent=2, default=str) + "\n", encoding="utf-8")
    return path


Say = Callable[[str], None]


def execute(run: Run, say: Say = print) -> Outcome:
    """Run the loop once, in order, and return what happened. Never raises for a refusal."""
    step_name = "signer"
    outcome = Outcome(ask=run.ask, kind="landed", step="receipt")

    def mark(label: str, text: str, ok: str = "ok") -> None:
        say(f"  [{ok:>4}] {label:<9} {text}")

    try:
        how = (
            "recorded, no key"
            if run.source == "recorded"
            else "genesis checked before each signature"
        )
        mark("signer", f"{run.signer.cluster} {run.signer.address} ({how})")

        step_name = "menu"
        read_menu(run)
        if run.menu is None:
            raise OrderBroken("read_menu left no menu")
        mark("menu", f"{run.menu.store}: {len(run.menu.products)} products, {run.menu.address}")

        step_name = "pin"
        pin_intent(run)
        if run.intent is None or run.intent_path is None or not Path(run.intent_path).is_file():
            raise OrderBroken("pin_intent must leave run.intent AND a file at run.intent_path")
        if read_pin(Path(run.intent_path)) != run.intent:
            raise OrderBroken("the pinned file does not say what run.intent says")
        outcome.intent_path = str(run.intent_path)
        mark(
            "pin",
            f"{run.intent.quantity} x {run.intent.product!r}, budget {run.intent.budget_raw}, "
            f"mint {run.intent.mint[:8]}..  -> {_short(run.intent_path, run.out)}",
        )

        step_name = "prepare"
        before_prepare = _now()
        if run.intent.pinned_at > before_prepare:
            raise OrderBroken("the pin is stamped after prepare started")
        prepare(run)
        if run.prepared is None or run.answer is None:
            raise OrderBroken("prepare must leave run.answer and run.prepared")
        remaining = run.prepared.blocks_remaining
        mark("prepare", f"simulated: {run.prepared.status}, expires in {remaining} blocks")

        step_name = "check"
        check(run)
        verdict = run.verdict
        if verdict is None:
            raise OrderBroken("check must leave run.verdict")
        outcome.checks = [r.line() for r in verdict.results]
        for result in verdict.results:
            if result.ok:  # a refusal is printed once, below, with its reason
                mark("check", result.line())
        if verdict.unwritten is not None:
            mark("check", f"{verdict.unwritten.what}: not written yet, so nothing signs", "todo")
            outcome.kind, outcome.step, outcome.detail = (
                "not-written",
                "check",
                str(verdict.unwritten),
            )
            return outcome
        if verdict.refusal is not None:
            raise Refused(verdict.refusal)
        if run.prepared.status != "pass":
            raise OrderBroken("the checks passed but the simulation did not: nothing signs")

        # The first ledger read, before anything is signed. Written for you.
        run.before = read_snapshot(run.chain, run.intent, run.prepared)

        if run.card == "stale":
            mark("card", "stale: waiting until the bytes expire", "card")
            run.chain.wait_past(run.prepared.last_valid_block_height)

        step_name = "sign"
        sign(run)
        if not run.signed:
            raise OrderBroken("sign must leave run.signed")
        outcome.signed = True
        mark("sign", f"signed by {run.signer.address or 'the recorded signature'}")

        if run.card == "tampered":
            run.signed = _tamper(run.signed)
            mark("card", "tampered: one byte of the signed bytes changed", "card")

        step_name = "verify"
        verify(run)
        if run.verified is None:
            raise OrderBroken("verify must leave run.verified")
        if not run.verified.get("verified"):
            raise Refused(
                FieldResult(
                    "signed bytes",
                    False,
                    "the prepared bytes, signed",
                    "binding matches" if run.verified.get("binding_matches") else "different bytes",
                    "verify",
                    str(run.verified.get("reason", ""))[:200],
                )
            )
        mark("verify", "the signed bytes are the prepared bytes")

        step_name = "submit"
        submit(run)
        sub = run.submitted
        if sub is None:
            raise OrderBroken("submit must leave run.submitted")
        if sub.get("refused") or not sub.get("confirmed"):
            outcome.kind, outcome.step = "gecko-refused", "submit"
            outcome.gecko_code = str(
                sub.get("code") or ("expired" if sub.get("expired") else "unconfirmed")
            )
            outcome.detail = str(sub.get("reason", ""))[:300]
            mark("submit", f"{outcome.gecko_code}: {outcome.detail}", "NO")
            outcome.record_path = str(_write_refusal(run, outcome))
            return outcome
        mark("submit", f"{sub.get('signature')} slot {sub.get('slot')}")

        step_name = "receipt"
        write_the_receipt(run)
        if run.receipt is None:
            raise OrderBroken("write_the_receipt must leave run.receipt")
        outcome.receipt = run.receipt
        outcome.record_path = str(write_receipt(run.receipt, run.out / "receipts"))
        r = run.receipt
        mark(
            "receipt",
            f"buyer {r.buyer_delta_raw:+d}, store {r.store_delta_raw:+d}, "
            f"total_purchases {r.total_purchases_before} to {r.total_purchases_after}",
            "ok" if r.reconciled else "NO",
        )
        say(f"  explorer: {r.explorer}")
        return outcome

    except NotYetWritten as todo:
        mark(step_name, f"{todo.what} is not written yet ({todo.hint}). Nothing signed.", "todo")
        outcome.kind, outcome.step, outcome.detail = "not-written", step_name, str(todo)
        return outcome
    except Refused as refused:
        outcome.kind, outcome.step, outcome.refusal = "refused", step_name, refused.result
        mark(step_name, f"REFUSED on {refused.result.line()}", "NO")
        say(f"  Nothing was {'submitted' if outcome.signed else 'signed'}.")
        outcome.record_path = str(_write_refusal(run, outcome))
        return outcome
    except GeckoRefused as gecko:
        outcome.kind, outcome.step, outcome.gecko_code = "gecko-refused", step_name, gecko.code
        outcome.detail = gecko.reason[:300]
        mark(step_name, f"Gecko refused, {gecko.code}: {outcome.detail}", "NO")
        outcome.record_path = str(_write_refusal(run, outcome))
        return outcome
    except (GeckoUnavailable, ChainError, LookupError, OSError) as down:
        outcome.kind, outcome.step, outcome.detail = "unavailable", step_name, str(down)[:300]
        mark(step_name, f"could not reach what this step needs: {outcome.detail}", "STOP")
        nothing = "submitted" if outcome.signed else "signed"
        say(f"  Nothing was {nothing}. To keep working offline: GECKO_SOURCE=recorded")
        return outcome
    except OrderBroken as broken:
        outcome.kind, outcome.step, outcome.detail = "order-broken", step_name, str(broken)
        mark(step_name, f"the loop's order was broken: {broken}", "STOP")
        return outcome
