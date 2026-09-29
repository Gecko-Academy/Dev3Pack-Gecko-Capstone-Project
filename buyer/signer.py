"""The only code in this repository that reads a key. Written for you: key handling is not
the lesson, and it is the easiest place to lose money.

Before EVERY signature, in this order, it refuses unless:

1. the prepared purchase says it was simulated on the cluster this signer serves;
2. the signer's own RPC answers with that cluster's genesis hash (a URL is not proof);
3. on mainnet (Friday only): the amount leaving the wallet is at or under the explicit
   `--mainnet-budget-raw` cap, and that cap is itself at or under `MAINNET_CAP_RAW`;
4. the chain has not passed `last_valid_block_height` (stale bytes are prepared again,
   never re-signed);
5. these exact bytes have not been signed before by this process;
6. this key is one of the transaction's required signers.

It signs the exact bytes it was given, once. It never prints, logs or returns key bytes.
"""

from __future__ import annotations

import base64
import json
import os
import subprocess
from pathlib import Path
from typing import Any, Protocol

from solders.keypair import Keypair
from solders.pubkey import Pubkey

from .chain import GENESIS
from .check import Refused, refuse
from .ledger import Chain
from .prepared import Prepared


def config_dir() -> Path:
    """Where keys live: ~/.config/dev3pack/, or DEV3PACK_HOME. Read at call time, not import."""
    return Path(os.environ.get("DEV3PACK_HOME", Path.home() / ".config" / "dev3pack"))


CONFIG_DIR = config_dir()

#: Friday's mainnet wallet file, made on the student's own machine by
#: `scripts/mainnet_wallet.py create`. The one mainnet key this repository ever reads.
MAINNET_WALLET = "mainnet-wallet.json"
#: The most any one mainnet signature may spend: three geckocoffee espressos at 100000 raw
#: USDC each (6 decimals, measured 28 September 2026), which is also everything the founder
#: funds a registered wallet with. A `--mainnet-budget-raw` above it is refused outright.
MAINNET_CAP_RAW = 300_000


def mainnet_wallet_path() -> Path:
    return config_dir() / MAINNET_WALLET


class KeyLocationError(RuntimeError):
    """The key file is missing, unreadable, or inside a git repository."""


class Signer(Protocol):
    cluster: str
    address: str

    def sign(self, prepared: Prepared) -> str: ...


def _refuse(field: str, asked: Any, found: Any, note: str = "") -> Refused:
    return Refused(refuse(field, asked, found, where="signer", note=note))


def inside_git_repo(path: Path) -> bool:
    try:
        out = subprocess.run(
            ["git", "-C", str(path.parent), "rev-parse", "--is-inside-work-tree"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return out.returncode == 0 and out.stdout.strip() == "true"


def load_keypair(path: Path) -> Keypair:
    """A keypair file from OUTSIDE any git repository. The bytes never leave this function."""
    path = Path(path).expanduser().resolve()
    if not path.is_file():
        raise KeyLocationError(f"no keypair file at {path}")
    if inside_git_repo(path):
        raise KeyLocationError(
            f"refusing to read a key inside a git repository ({path}). "
            "Keys live in ~/.config/dev3pack/, never in a repo."
        )
    try:
        return Keypair.from_bytes(bytes(json.loads(path.read_text(encoding="utf-8"))))
    except (ValueError, TypeError) as exc:
        # The message names the file, never its contents.
        raise KeyLocationError(f"{path} is not a Solana keypair file") from exc


def _compact_u16(raw: bytes, at: int) -> tuple[int, int]:
    value = shift = 0
    while True:
        byte = raw[at]
        at += 1
        value |= (byte & 0x7F) << shift
        if not byte & 0x80:
            return value, at
        shift += 7


def signer_slot(raw: bytes, key: Pubkey) -> tuple[int, int, bytes]:
    """(slot, first signature offset, message bytes) for `key` in a serialized transaction."""
    count, at = _compact_u16(raw, 0)
    message = raw[at + 64 * count :]
    offset = 1 if message[0] & 0x80 else 0  # a v0 message starts with its version byte
    required = message[offset]
    n_keys, keys_at = _compact_u16(message, offset + 3)
    keys = [bytes(message[keys_at + 32 * i : keys_at + 32 * (i + 1)]) for i in range(n_keys)]
    if bytes(key) not in keys[:required]:
        raise _refuse("signer", str(key), "not a required signer of these bytes")
    return keys.index(bytes(key)), at, message


class _Guarded:
    """Every guard, shared by the real signer and the recorded one."""

    def __init__(self, cluster: str, chain: Chain, budget_raw: int | None = None) -> None:
        if cluster == "mainnet" and budget_raw is None:
            raise KeyLocationError("mainnet signing needs an explicit --mainnet-budget-raw cap")
        if cluster == "mainnet" and budget_raw is not None and budget_raw > MAINNET_CAP_RAW:
            raise KeyLocationError(
                f"--mainnet-budget-raw {budget_raw} is above Friday's cap of {MAINNET_CAP_RAW}"
            )
        if cluster not in GENESIS:
            raise KeyLocationError(f"unknown cluster {cluster!r}")
        self.cluster = cluster
        self.chain = chain
        self.budget_raw = budget_raw
        self._signed: set[str] = set()
        self.address = ""

    def guard(self, prepared: Prepared) -> None:
        if prepared.network != self.cluster:
            raise _refuse("network", self.cluster, prepared.network)
        genesis = self.chain.genesis()
        if genesis != GENESIS[self.cluster]:
            raise _refuse("cluster", GENESIS[self.cluster], genesis, note="genesis hash of the RPC")
        if self.cluster == "mainnet":
            assert self.budget_raw is not None
            if prepared.price_raw is None:
                raise _refuse("mainnet budget", self.budget_raw, None, note="no simulated amount")
            if prepared.price_raw > self.budget_raw:
                raise _refuse("mainnet budget", f"at most {self.budget_raw}", prepared.price_raw)
        height = self.chain.block_height()
        if height > prepared.last_valid_block_height:
            raise _refuse(
                "blockhash",
                f"height <= {prepared.last_valid_block_height}",
                height,
                note="stale bytes: prepare again, never re-sign",
            )
        if prepared.binding in self._signed:
            raise _refuse("binding", "bytes signed once", "these bytes were already signed")
        if prepared.buyer != self.address:
            raise _refuse("buyer", self.address, prepared.buyer)


class KeypairSigner(_Guarded):
    def __init__(
        self, keypair_path: Path, cluster: str, chain: Chain, budget_raw: int | None = None
    ) -> None:
        super().__init__(cluster, chain, budget_raw)
        self._key = load_keypair(keypair_path)
        self.address = str(self._key.pubkey())

    def sign(self, prepared: Prepared) -> str:
        self.guard(prepared)
        raw = bytearray(base64.b64decode(prepared.unsigned_transaction))
        slot, first, message = signer_slot(bytes(raw), self._key.pubkey())
        raw[first + 64 * slot : first + 64 * (slot + 1)] = bytes(self._key.sign_message(message))
        self._signed.add(prepared.binding)
        return base64.b64encode(bytes(raw)).decode()

    def __repr__(self) -> str:
        return f"KeypairSigner({self.cluster}, {self.address})"


class RecordedSigner(_Guarded):
    """No key. Runs every guard against the recorded chain, then hands back the signed
    bytes the fixture recorded for exactly these unsigned bytes."""

    def __init__(self, fixture: dict[str, Any], chain: Chain) -> None:
        super().__init__(fixture.get("ledger", {}).get("cluster", "devnet"), chain)
        self.fixture = fixture
        self.address = fixture.get("context", {}).get("buyer", "")

    def sign(self, prepared: Prepared) -> str:
        self.guard(prepared)
        recorded = self.fixture.get("signed_transaction")
        unsigned = self.fixture.get("calls", {}).get("prepare_purchase", {})
        if not recorded or unsigned.get("transaction", {}).get("unsigned_transaction") != (
            prepared.unsigned_transaction
        ):
            raise _refuse(
                "signer", "recorded signature", "none for these bytes", note="recorded lane"
            )
        self._signed.add(prepared.binding)
        return str(recorded)
