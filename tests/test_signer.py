"""The signer refuses before it signs: wrong cluster, stale bytes, no cap, wrong key."""

from __future__ import annotations

import base64
import dataclasses
import json
import subprocess
from pathlib import Path

import pytest
from conftest import fixture
from solders.keypair import Keypair
from solders.message import Message
from solders.system_program import TransferParams, transfer
from solders.transaction import Transaction

from buyer import cli
from buyer.chain import DEVNET_GENESIS, MAINNET_GENESIS
from buyer.check import Refused
from buyer.prepared import Prepared
from buyer.signer import MAINNET_CAP_RAW, KeyLocationError, KeypairSigner, mainnet_wallet_path


class FakeChain:
    def __init__(self, genesis: str = DEVNET_GENESIS, height: int = 100) -> None:
        self.cluster, self.rpc_url = "devnet", "https://devnet.invalid"
        self._genesis, self._height = genesis, height

    def genesis(self) -> str:
        return self._genesis

    def block_height(self) -> int:
        return self._height

    def store(self, name: str) -> None:
        return None

    def token_balance(self, owner: str, mint: str) -> int:
        return 0

    def wait_past(self, height: int) -> None:
        self._height = height + 1


def keyfile(tmp_path: Path) -> tuple[Path, Keypair]:
    key = Keypair()
    path = tmp_path / "devnet-buyer.json"
    path.write_text(json.dumps(list(bytes(key))))
    return path, key


def prepared_for(key: Keypair, network: str = "devnet", price: int = 1_000_000) -> Prepared:
    """A real prepared answer, with its bytes swapped for a tiny transaction `key` must sign."""
    message = Message(
        [transfer(TransferParams(from_pubkey=key.pubkey(), to_pubkey=key.pubkey(), lamports=1))],
        key.pubkey(),
    )
    unsigned = base64.b64encode(bytes(Transaction.new_unsigned(message))).decode()
    real = Prepared.from_answer(fixture("cases/1-espresso")["calls"]["prepare_purchase"])
    return dataclasses.replace(
        real,
        buyer=str(key.pubkey()),
        network=network,
        price_raw=price,
        last_valid_block_height=200,
        unsigned_transaction=unsigned,
    )


def test_signs_the_exact_bytes_once_on_devnet(tmp_path: Path) -> None:
    path, key = keyfile(tmp_path)
    signer = KeypairSigner(path, "devnet", FakeChain())
    prepared = prepared_for(key)
    signed = Transaction.from_bytes(base64.b64decode(signer.sign(prepared)))
    signed.verify()  # raises if the signature is not over these bytes
    with pytest.raises(Refused, match="binding"):
        signer.sign(prepared)


def test_refuses_a_node_that_is_not_devnet(tmp_path: Path) -> None:
    path, key = keyfile(tmp_path)
    signer = KeypairSigner(path, "devnet", FakeChain(genesis=MAINNET_GENESIS))
    with pytest.raises(Refused) as caught:
        signer.sign(prepared_for(key))
    assert caught.value.result.field == "cluster"
    assert caught.value.result.found == MAINNET_GENESIS


def test_refuses_bytes_prepared_for_another_network(tmp_path: Path) -> None:
    path, key = keyfile(tmp_path)
    signer = KeypairSigner(path, "devnet", FakeChain())
    with pytest.raises(Refused) as caught:
        signer.sign(prepared_for(key, network="mainnet"))
    assert caught.value.result.field == "network"


def test_refuses_stale_bytes(tmp_path: Path) -> None:
    path, key = keyfile(tmp_path)
    signer = KeypairSigner(path, "devnet", FakeChain(height=201))
    with pytest.raises(Refused) as caught:
        signer.sign(prepared_for(key))
    assert caught.value.result.field == "blockhash"


def test_refuses_bytes_another_key_must_sign(tmp_path: Path) -> None:
    path, _ = keyfile(tmp_path)
    signer = KeypairSigner(path, "devnet", FakeChain())
    with pytest.raises(Refused) as caught:
        signer.sign(prepared_for(Keypair()))
    assert caught.value.result.field == "buyer"


def test_mainnet_needs_an_explicit_cap(tmp_path: Path) -> None:
    path, _ = keyfile(tmp_path)
    with pytest.raises(KeyLocationError, match="mainnet-budget-raw"):
        KeypairSigner(path, "mainnet", FakeChain(genesis=MAINNET_GENESIS))


def test_mainnet_refuses_above_the_cap_before_signing(tmp_path: Path) -> None:
    """Friday mode, checked offline against a fake node. Nothing here reaches mainnet."""
    path, key = keyfile(tmp_path)
    signer = KeypairSigner(path, "mainnet", FakeChain(genesis=MAINNET_GENESIS), budget_raw=100_000)
    with pytest.raises(Refused) as caught:
        signer.guard(prepared_for(key, network="mainnet", price=100_001))
    assert caught.value.result.field == "mainnet budget"
    assert caught.value.result.found == 100_001
    signer.guard(prepared_for(key, network="mainnet", price=100_000))  # at the cap: allowed


def test_mainnet_refuses_when_no_amount_was_simulated(tmp_path: Path) -> None:
    path, key = keyfile(tmp_path)
    signer = KeypairSigner(path, "mainnet", FakeChain(genesis=MAINNET_GENESIS), budget_raw=100_000)
    with pytest.raises(Refused):
        signer.guard(dataclasses.replace(prepared_for(key, network="mainnet"), price_raw=None))


def test_refuses_a_key_inside_a_git_repository(tmp_path: Path) -> None:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    path, _ = keyfile(tmp_path)
    with pytest.raises(KeyLocationError, match="inside a git repository"):
        KeypairSigner(path, "devnet", FakeChain())


def test_the_key_never_shows_in_repr_or_errors(tmp_path: Path) -> None:
    path, key = keyfile(tmp_path)
    signer = KeypairSigner(path, "devnet", FakeChain(genesis=MAINNET_GENESIS))
    secret = str(list(bytes(key)))
    with pytest.raises(Refused) as caught:
        signer.sign(prepared_for(key))
    assert secret not in repr(signer)
    assert secret not in str(caught.value)
    assert str(key) not in repr(signer) + str(caught.value)


def test_mainnet_refuses_a_cap_above_fridays_ceiling(tmp_path: Path) -> None:
    path, _ = keyfile(tmp_path)
    chain = FakeChain(genesis=MAINNET_GENESIS)
    with pytest.raises(KeyLocationError, match="above Friday's cap"):
        KeypairSigner(path, "mainnet", chain, budget_raw=MAINNET_CAP_RAW + 1)
    KeypairSigner(path, "mainnet", chain, budget_raw=MAINNET_CAP_RAW)  # at the ceiling: allowed


def test_the_mainnet_lane_reads_the_registered_wallet_and_defaults_to_the_cap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`--mainnet` with no key flag and no budget flag: the wallet `mainnet_wallet.py create`
    made, capped at 300000. Built offline; nothing is prepared, signed or sent."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("DEV3PACK_HOME", raising=False)
    key = Keypair()
    wallet = mainnet_wallet_path()
    wallet.parent.mkdir(parents=True)
    wallet.write_text(json.dumps(list(bytes(key))))
    args = cli.build_parser().parse_args(
        ["one espresso", "--mainnet", "--store", "geckocoffee", "--out", str(tmp_path)]
    )
    run = cli.live_run(args, args.ask, {})
    assert run.signer.address == str(key.pubkey())
    assert run.signer.budget_raw == MAINNET_CAP_RAW == 300_000  # type: ignore[attr-defined]
    assert run.context.pay_mint == cli.MAINNET_USDC


def test_the_mainnet_lane_without_a_wallet_says_create_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("DEV3PACK_HOME", raising=False)
    args = cli.build_parser().parse_args(
        ["one espresso", "--mainnet", "--store", "geckocoffee", "--out", str(tmp_path)]
    )
    with pytest.raises(SystemExit, match="mainnet_wallet.py create"):
        cli.live_run(args, args.ask, {})
