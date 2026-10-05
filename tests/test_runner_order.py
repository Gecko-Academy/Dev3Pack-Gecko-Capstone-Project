"""The runner enforces the order: nothing signs before a pin, a prepare and a passing check.

These tests swap the step bodies for tiny fakes, so they hold whether or not you have
written yours.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path
from typing import Any

import pytest
from conftest import fixture

from buyer import agent
from buyer.check import FieldResult, NotYetWritten, Verdict
from buyer.cli import recorded_run
from buyer.intent import IntentRecord, pin


class SpySigner:
    cluster, address = "devnet", "spy"

    def __init__(self) -> None:
        self.calls = 0

    def sign(self, prepared: Any) -> str:
        self.calls += 1
        return "signed"


def run_for(tmp_path: Path, name: str = "cases/1-espresso") -> agent.Run:
    run = recorded_run(fixture(name), tmp_path)
    run.signer = SpySigner()
    return run


def pinned(run: agent.Run) -> IntentRecord:
    ctx = run.context
    return IntentRecord(
        ask=run.ask,
        store=ctx.store,
        product="Espresso",
        quantity=1,
        budget_raw=ctx.budget_raw,
        mint=ctx.pay_mint,
        buyer=ctx.buyer,
        network=ctx.network,
        store_authority="Dt8quRFWgTMrrDgVa4GGFRJWksncskbs1tpYAQHkEPwJ",
        menu_price_raw=1_000_000,
    )


def test_the_template_stops_at_the_first_unwritten_step_and_signs_nothing(tmp_path: Path) -> None:
    run = run_for(tmp_path)
    outcome = agent.execute(run, say=lambda _: None)
    if outcome.kind != "not-written":
        pytest.skip("your steps are written: this test is about the untouched template")
    assert run.signer.calls == 0  # type: ignore[attr-defined]


def test_a_pin_that_is_not_on_disk_stops_the_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run = run_for(tmp_path)

    def pin_in_memory_only(r: agent.Run) -> None:
        r.intent = pinned(r)
        r.intent_path = tmp_path / "never-written.json"

    monkeypatch.setattr(agent, "pin_intent", pin_in_memory_only)
    outcome = agent.execute(run, say=lambda _: None)
    assert outcome.kind == "order-broken" and outcome.step == "pin"
    assert run.signer.calls == 0  # type: ignore[attr-defined]


def test_a_refusing_check_means_no_signature(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run = run_for(tmp_path)
    monkeypatch.setattr(agent, "pin_intent", _pin)
    monkeypatch.setattr(agent, "prepare", _prepare)
    refusal = FieldResult("quantity", False, 2, 1)
    monkeypatch.setattr(agent, "check", lambda r: setattr(r, "verdict", Verdict([], refusal)))
    outcome = agent.execute(run, say=lambda _: None)
    assert outcome.kind == "refused" and outcome.refusal == refusal
    assert run.signer.calls == 0  # type: ignore[attr-defined]
    assert outcome.record_path and Path(outcome.record_path).is_file()


def test_an_unwritten_check_is_a_refusal_not_a_pass(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run = run_for(tmp_path)
    monkeypatch.setattr(agent, "pin_intent", _pin)
    monkeypatch.setattr(agent, "prepare", _prepare)
    todo = NotYetWritten("check_product", "test-only unfinished check")
    monkeypatch.setattr(
        agent,
        "check",
        lambda r: setattr(r, "verdict", Verdict(unwritten=todo)),
    )
    monkeypatch.setattr(agent, "sign", lambda r: setattr(r, "signed", r.signer.sign(r.prepared)))
    outcome = agent.execute(run, say=lambda _: None)

    assert outcome.kind == "not-written"
    assert run.signer.calls == 0  # type: ignore[attr-defined]


def test_a_failed_simulation_never_signs_even_if_checks_pass(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run = run_for(tmp_path)
    monkeypatch.setattr(agent, "pin_intent", _pin)

    def prepare_failed(r: agent.Run) -> None:
        _prepare(r)
        r.prepared = dataclasses.replace(r.prepared, status="fail")

    monkeypatch.setattr(agent, "prepare", prepare_failed)
    monkeypatch.setattr(agent, "check", lambda r: setattr(r, "verdict", Verdict([])))
    outcome = agent.execute(run, say=lambda _: None)
    assert outcome.kind == "order-broken"
    assert run.signer.calls == 0  # type: ignore[attr-defined]


def _pin(run: agent.Run) -> None:
    run.intent = pinned(run)
    run.intent_path = pin(run.intent, run.out / "intents")


def _prepare(run: agent.Run) -> None:
    from buyer.prepared import Prepared

    run.answer = run.gecko.call("prepare_purchase", {})
    run.prepared = Prepared.from_answer(run.answer)
