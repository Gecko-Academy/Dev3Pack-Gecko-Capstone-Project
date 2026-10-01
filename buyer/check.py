"""The part that says no: seven fields of the prepared purchase against the pinned intent.

Each check returns a `FieldResult`. A refusal names the field and BOTH values: what was
asked (from the pin) and what was found (in the prepared bytes). "Cannot buy" is not a
refusal; "price_raw: asked at most 2000000, prepared 3000000" is.

Two checks are written as worked examples: `check_program` and `check_store`. The other
five are yours. Until you write one it raises `NotYetWritten`, and `check_all` treats that
as a refusal: an unwritten check never lets a signature through.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from . import letmebuy

if TYPE_CHECKING:
    from .intent import IntentRecord
    from .prepared import Prepared


class NotYetWritten(NotImplementedError):
    """A TODO the student has not written yet. Never caught as a pass."""

    def __init__(self, what: str, hint: str) -> None:
        self.what, self.hint = what, hint
        super().__init__(f"{what} is not written yet ({hint})")


@dataclass(frozen=True)
class FieldResult:
    field: str
    ok: bool
    asked: Any
    found: Any
    #: where `found` came from: "prepared", "menu", "signer", "verify"
    where: str = "prepared"
    note: str = ""

    def line(self) -> str:
        if self.ok:
            return f"{self.field}: {self.found!r}"
        text = f"{self.field}: asked {self.asked!r}, {self.where} {self.found!r}"
        return f"{text} ({self.note})" if self.note else text


class Refused(Exception):
    """Raised from any step that decides not to go on. Carries the field that decided."""

    def __init__(self, result: FieldResult) -> None:
        self.result = result
        super().__init__(result.line())


def refuse(
    field_name: str, asked: Any, found: Any, where: str = "prepared", note: str = ""
) -> FieldResult:
    return FieldResult(field_name, False, asked, found, where, note)


def agree(field_name: str, value: Any) -> FieldResult:
    return FieldResult(field_name, True, value, value)


# --- worked example 1 ---------------------------------------------------------------------


def check_program(intent: IntentRecord, prepared: Prepared) -> FieldResult:
    """The bytes call the store program, and nothing else that could move money.

    Compared as an address. `letmebuy.program_id()` comes from the IDL shipped in this
    repo, not from Gecko's answer: the thing being checked never supplies the answer.
    """
    expected = str(letmebuy.program_id())
    if prepared.program != expected:
        return refuse("program", expected, prepared.program)
    if prepared.programs != (expected,):
        return refuse(
            "program", [expected], list(prepared.programs), note="an extra program is called"
        )
    return agree("program", expected)


# --- worked example 2 ---------------------------------------------------------------------


def check_store(intent: IntentRecord, prepared: Prepared) -> FieldResult:
    """The store account is the one DERIVED from the pinned store name.

    Never a constant, and never the address Gecko reported: PDA(['receipts', name]) is
    computed here, from the name the person asked for. A store with a similar name, or a
    swapped account, gives a different address.
    """
    expected = str(letmebuy.store_address(intent.store))
    if prepared.store != expected:
        return refuse("store", f"{intent.store} at {expected}", prepared.store)
    return agree("store", expected)


# --- yours --------------------------------------------------------------------------------


def check_product(intent: IntentRecord, prepared: Prepared) -> FieldResult:
    """
    PINNED:   intent.product
    PREPARED: prepared.product

    Defense:
    The prepared purchase must agree with the product the user requested.

    Agree → continue.
    Disagree → refuse and show both values.

    Current policy:
    Exact product-name equality.
    Broader matching/normalization is a separate design decision.
    """
    if prepared.product != intent.product:
        return refuse(
            "product",
            intent.product,
            prepared.product,
        )
    return agree("product", intent.product)


def check_price(intent: IntentRecord, prepared: Prepared) -> FieldResult:
    """
    PINNED:   intent.budget_raw
    PREPARED: prepared.price_raw

    Defense:
    The prepared amount must be at or below the spending limit the user pinned.

    Known amount:
        prepared.price_raw <= intent.budget_raw → AGREE
        prepared.price_raw > intent.budget_raw  → REFUSE

    No simulated amount:
        prepared.price_raw is None → REFUSE

    Important:
    This check enforces the budget ceiling.
    It does not currently establish that the prepared amount equals the menu price.
    """
    if prepared.price_raw is None:
        return refuse(
            "price_raw",
            intent.budget_raw,
            None,
            note="no amount was simulated",
        )
    if prepared.price_raw > intent.budget_raw:
        return refuse(
            "price_raw",
            intent.budget_raw,
            prepared.price_raw,
        )
    return agree("price_raw", prepared.price_raw)


def check_mint(intent: IntentRecord, prepared: Prepared) -> FieldResult:
    """TODO: the token paid is the pinned mint, compared as an ADDRESS.

    Use case 3 ("module 3, paid in USDC") must refuse a token called USDC at another
    address. There is no symbol anywhere in `Prepared`, on purpose.
    """
    raise NotYetWritten("check_mint", "buyer/check.py: compare prepared.mint with the pin")


def check_quantity(intent: IntentRecord, prepared: Prepared) -> FieldResult:
    """TODO: the number of purchases in the bytes is the number asked for.

    `prepare_purchase` prepares one unit. Use case 5 ("two bags of beans") must refuse:
    asked 2, prepared 1. Refusing is the honest answer; buying one is not what was asked.
    """
    raise NotYetWritten("check_quantity", "buyer/check.py: compare prepared.quantity with the pin")


def check_destination(intent: IntentRecord, prepared: Prepared) -> FieldResult:
    """TODO: the money goes to the store's own token account for the pinned mint.

    The destination is the associated token account of the authority the menu showed when
    you pinned (`intent.store_authority`) for the pinned mint. Derive it with
    `letmebuy.token_account(...)`; never copy it from Gecko's answer.
    """
    raise NotYetWritten("check_destination", "buyer/check.py: derive and compare the destination")


#: The order is part of the design: cheap, structural checks first.
CHECKS: tuple[Callable[[IntentRecord, Prepared], FieldResult], ...] = (
    check_program,
    check_store,
    check_product,
    check_price,
    check_mint,
    check_quantity,
    check_destination,
)


@dataclass
class Verdict:
    results: list[FieldResult] = field(default_factory=list)
    refusal: FieldResult | None = None
    unwritten: NotYetWritten | None = None

    @property
    def passed(self) -> bool:
        return self.refusal is None and self.unwritten is None


def check_all(intent: IntentRecord, prepared: Prepared) -> Verdict:
    """Run every check in order and stop at the first that does not agree."""
    verdict = Verdict()
    for check in CHECKS:
        try:
            result = check(intent, prepared)
        except NotYetWritten as todo:
            verdict.unwritten = todo
            return verdict
        verdict.results.append(result)
        if not result.ok:
            verdict.refusal = result
            return verdict
    return verdict
