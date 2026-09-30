"""The recorded lane: real devnet answers, replayed offline, through the same code path."""

from __future__ import annotations

import pytest
from conftest import case_names, fixture

from buyer.cli import main, matches
from buyer.mcp_client import RecordedGecko, RecordedMiss

FIELDS = {
    "program",
    "store",
    "product",
    "price_raw",
    "mint",
    "quantity",
    "destination",
    "signed bytes",
    "blockhash",
}


@pytest.mark.parametrize("name", case_names("cases") + case_names("cards"))
def test_every_fixture_says_what_it_expects(name: str) -> None:
    f = fixture(name)
    assert f["ask"] and f["context"]["store"] == "dev3pack-cafe"
    assert f["calls"]["list_stores"]["network"] == "devnet"
    expected = f["expected"]
    assert expected["outcome"] in {"landed", "refused"}
    if expected["outcome"] == "refused":
        fields = expected["field"] if isinstance(expected["field"], list) else [expected["field"]]
        assert set(fields) <= FIELDS


def test_the_landing_fixture_has_the_whole_trip() -> None:
    f = fixture("cases/1-espresso")
    assert {"prepare_purchase", "verify_signed_transaction", "submit_transaction"} <= set(
        f["calls"]
    )
    assert f["calls"]["submit_transaction"]["confirmed"] is True
    assert len(f["ledger"]["reads"]) == 2


def test_recorded_verify_refuses_bytes_it_did_not_record() -> None:
    gecko = RecordedGecko(fixture("cards/tampered"))
    answer = gecko.call("verify_signed_transaction", {"transaction": "something else"})
    assert answer["verified"] is False and answer["binding_matches"] is False


def test_a_missing_recording_is_named() -> None:
    with pytest.raises(RecordedMiss, match="submit_transaction"):
        RecordedGecko(fixture("cases/5-beans")).call("submit_transaction", {})


def test_the_cases_run_offline_end_to_end(tmp_path, capsys) -> None:  # type: ignore[no-untyped-def]
    code = main(["--cases", "--recorded", "--out", str(tmp_path)])
    out = capsys.readouterr().out
    assert "cases match what the fixtures expect" in out
    assert code in (0, 1)  # 1 until your steps and checks are written


def test_matches_accepts_any_listed_field() -> None:
    from buyer.agent import Outcome
    from buyer.check import FieldResult

    refused = Outcome("one latte", "refused", "check", FieldResult("product", False, "a", "b"))
    assert matches({"outcome": "refused", "field": ["price_raw", "product"]}, refused)
    assert not matches({"outcome": "refused", "field": "quantity"}, refused)


@pytest.mark.parametrize(("card", "field"), [("tampered", "signed bytes"), ("stale", "blockhash")])
def test_a_single_ask_with_a_card_replays_that_card(card: str, field: str) -> None:
    # "one espresso" is also case 1, which has no answer for tampered bytes. With --card,
    # the card's own recording is the one that was asked for.
    from buyer.cli import _fixture_for

    assert _fixture_for("one espresso", card)["expected"]["field"] == field
    assert _fixture_for("one espresso")["expected"]["outcome"] == "landed"
