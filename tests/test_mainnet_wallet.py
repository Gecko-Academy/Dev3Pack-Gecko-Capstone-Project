"""Friday's wallet script, offline: a real throwaway key under a scratch HOME, and a fake
registry. Nothing here reaches Gecko or mainnet (conftest blocks the network)."""

from __future__ import annotations

import importlib.util
import json
import stat
from pathlib import Path
from typing import Any

import pytest
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.signature import Signature

from buyer import chain
from buyer.chain import MAINNET_GENESIS

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location(
    "mainnet_wallet", ROOT / "scripts" / "mainnet_wallet.py"
)
assert spec and spec.loader
wallet = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wallet)

GECKO_KEY = "gk_live_" + "s3cr3t" * 6
CHALLENGE = "dev3pack 2026-09 class wallet 7f3a91 expires 2026-10-02T12:00:00Z"


@pytest.fixture
def home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("DEV3PACK_HOME", raising=False)
    monkeypatch.setenv("GECKO_API_KEY", GECKO_KEY)
    return tmp_path


def key_file(home: Path) -> Path:
    return home / ".config" / "dev3pack" / "mainnet-wallet.json"


class FakeRegistry:
    """The registry's contract, as the server lane specified it. Records what it was sent."""

    def __init__(
        self,
        post: tuple[int, Any] | None = None,
        get: tuple[int, Any] | None = None,
        replaced: bool = False,
    ):
        self.get, self.post, self.replaced = get, post, replaced
        self.issued: list[str] = []
        self.calls: list[tuple[str, str, dict[str, str], Any]] = []

    def __call__(
        self, method: str, url: str, headers: dict[str, str], body: dict[str, Any] | None
    ) -> tuple[int, Any]:
        self.calls.append((method, url, headers, body))
        if method == "GET":
            if self.get:
                return self.get
            # Single-use, like the server's: every GET issues a different challenge.
            self.issued.append(f"{CHALLENGE} #{len(self.issued) + 1}")
            return 200, {"challenge": self.issued[-1], "expires_at": "2026-10-02T12:00:00Z"}
        assert body is not None
        return self.post or (
            200,
            {
                "account": "student@example.com",
                "cohort": body["cohort"],
                "address": body["address"],
                "registered": True,
                "replaced": self.replaced,
            },
        )


def created(home: Path, capsys: pytest.CaptureFixture[str]) -> tuple[Keypair, str]:
    assert wallet.main(["create"]) == 0
    out = capsys.readouterr().out
    key = Keypair.from_bytes(bytes(json.loads(key_file(home).read_text())))
    return key, out


def test_create_makes_a_600_key_outside_the_repo_and_prints_only_the_address(
    home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    key, out = created(home, capsys)
    assert stat.S_IMODE(key_file(home).stat().st_mode) == 0o600
    assert str(key.pubkey()) in out
    assert str(list(bytes(key))) not in out
    assert str(key) not in out  # the base58 secret form, too


def test_create_refuses_to_overwrite_a_wallet(
    home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    created(home, capsys)
    before = key_file(home).read_bytes()
    assert wallet.main(["create"]) == 1
    assert "already exists" in capsys.readouterr().out
    assert key_file(home).read_bytes() == before


def test_register_signs_the_challenge_with_the_wallet_key(
    home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    key, _ = created(home, capsys)
    registry = FakeRegistry()
    assert wallet.main(["register"], transport=registry) == 0

    (get, post) = registry.calls
    assert get[0] == "GET" and get[1].endswith("/registry/class-wallet/challenge?cohort=2026-09")
    assert post[0] == "POST" and post[1].endswith("/registry/class-wallet")
    assert get[2]["authorization"] == post[2]["authorization"] == f"Bearer {GECKO_KEY}"
    body = post[3]
    assert body["cohort"] == "2026-09"
    assert body["address"] == str(key.pubkey())
    assert body["challenge"] == registry.issued[0]
    signature = Signature.from_string(body["signature"])
    assert signature.verify(Pubkey.from_string(body["address"]), body["challenge"].encode())
    assert f"registered {key.pubkey()} for student@example.com" in capsys.readouterr().out


def test_the_keys_never_reach_the_output_or_the_request_body(
    home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    key, _ = created(home, capsys)
    registry = FakeRegistry()
    wallet.main(["register"], transport=registry)
    wallet.main(["register"], transport=FakeRegistry(post=(400, {"error": GECKO_KEY})))
    out = capsys.readouterr().out
    assert GECKO_KEY not in out
    assert str(key) not in out and str(list(bytes(key))) not in out
    sent = json.dumps(registry.calls[1][3])
    assert str(key) not in sent and GECKO_KEY not in sent


@pytest.mark.parametrize(
    ("status", "code", "error"),
    [
        (401, "key-invalid", "That Gecko key is not valid. Run `gecko login` again."),
        (429, "rate-limited", "Too many requests from this address."),
        (403, "not-granted", "Your account is not in the 2026-09 class yet."),
        (400, "challenge-invalid", "The challenge expired or was already used."),
        (400, "address-invalid", "That is not a Solana address."),
        (400, "signature-invalid", "The signature does not match the address."),
    ],
)
def test_each_refusal_prints_the_servers_message(
    home: Path, capsys: pytest.CaptureFixture[str], status: int, code: str, error: str
) -> None:
    created(home, capsys)
    body = {"error": error, "code": code}
    assert wallet.main(["register"], transport=FakeRegistry(post=(status, body))) == 1
    out = capsys.readouterr().out
    assert error in out and code in out
    assert "registered " not in out


def test_a_refused_challenge_stops_before_anything_is_signed(
    home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    created(home, capsys)
    registry = FakeRegistry(get=(401, {"error": "Unknown Gecko key.", "code": "key-invalid"}))
    assert wallet.main(["register"], transport=registry) == 1
    assert [c[0] for c in registry.calls] == ["GET"]
    assert "Unknown Gecko key." in capsys.readouterr().out


def test_not_enabled_yet_says_so(home: Path, capsys: pytest.CaptureFixture[str]) -> None:
    created(home, capsys)
    assert wallet.main(["register"], transport=FakeRegistry(get=(503, None))) == 1
    assert "503" in capsys.readouterr().out


def test_register_without_a_wallet_says_create_first(
    home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    registry = FakeRegistry()
    assert wallet.main(["register"], transport=registry) == 1
    assert "create" in capsys.readouterr().out
    assert registry.calls == []


def test_show_reads_mainnet_balances_and_signs_nothing(
    home: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    key, _ = created(home, capsys)
    asked: list[str] = []

    def fake_rpc(
        url: str, method: str, params: list[Any] | None = None, timeout: float = 30
    ) -> Any:
        asked.append(method)
        return {
            "getGenesisHash": MAINNET_GENESIS,
            "getBalance": {"value": 9_400_000},
            "getTokenAccountBalance": {"value": {"amount": "300000"}},
        }[method]

    monkeypatch.setattr(chain, "rpc", fake_rpc)
    assert wallet.main(["show"]) == 0
    out = capsys.readouterr().out
    assert str(key.pubkey()) in out
    assert "0.009400" in out and "300000 raw" in out
    assert asked == ["getGenesisHash", "getBalance", "getTokenAccountBalance"]


def test_show_refuses_a_node_that_is_not_mainnet(
    home: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    created(home, capsys)
    monkeypatch.setattr(chain, "rpc", lambda *_a, **_k: chain.DEVNET_GENESIS)
    assert wallet.main(["show"]) == 1
    assert "genesis" in capsys.readouterr().out


def test_no_gecko_key_stops_before_any_request(
    home: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    created(home, capsys)
    monkeypatch.delenv("GECKO_API_KEY")

    def no_terminal(prompt: str = "") -> str:
        raise EOFError

    monkeypatch.setattr(wallet.getpass, "getpass", no_terminal)
    monkeypatch.setattr(wallet.sys.stdin, "isatty", lambda: True)
    registry = FakeRegistry()
    assert wallet.main(["register"], transport=registry) == 1
    assert "no Gecko key" in capsys.readouterr().out
    assert registry.calls == []


def test_a_bad_cohort_on_the_challenge_prints_the_servers_message(
    home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    created(home, capsys)
    body = {"error": "cohort must be one of: 2026-09", "code": "cohort-invalid"}
    registry = FakeRegistry(get=(400, body))
    assert wallet.main(["register"], transport=registry) == 1
    out = capsys.readouterr().out
    assert "cohort must be one of: 2026-09" in out and "cohort-invalid" in out
    assert registry.calls[0][1].endswith("?cohort=2026-09")
    assert [c[0] for c in registry.calls] == ["GET"]


@pytest.mark.parametrize("method", ["GET", "POST"])
def test_rate_limited_says_wait_a_minute_and_does_not_loop(
    home: Path, capsys: pytest.CaptureFixture[str], method: str
) -> None:
    created(home, capsys)
    limited = (429, {"error": "Too many requests from this address.", "code": "rate-limited"})
    registry = FakeRegistry(**({"get": limited} if method == "GET" else {"post": limited}))
    assert wallet.main(["register"], transport=registry) == 1
    out = capsys.readouterr().out
    assert "Too many requests from this address." in out
    assert "wait a minute and run register again" in out
    assert [c[0] for c in registry.calls] == (["GET"] if method == "GET" else ["GET", "POST"])


def test_every_run_fetches_a_fresh_challenge_even_after_a_failed_post(
    home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The server consumes a challenge before it checks the signature: a failed POST burns
    it. So a second run must never send the first run's challenge again."""
    created(home, capsys)
    burnt = FakeRegistry(post=(400, {"error": "bad signature", "code": "signature-invalid"}))
    assert wallet.main(["register"], transport=burnt) == 1
    burnt.post = None
    assert wallet.main(["register"], transport=burnt) == 0
    assert [c[0] for c in burnt.calls] == ["GET", "POST", "GET", "POST"]
    first, second = burnt.calls[1][3]["challenge"], burnt.calls[3][3]["challenge"]
    assert first != second and second == burnt.issued[1]


def test_a_second_address_from_this_machine_warns_and_waits_for_replace(
    home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    old, _ = created(home, capsys)
    assert wallet.main(["register"], transport=FakeRegistry()) == 0
    key_file(home).unlink()  # the student made a new wallet; the old one may hold money
    new, _ = created(home, capsys)

    registry = FakeRegistry(replaced=True)
    assert wallet.main(["register"], transport=registry) == 1
    out = capsys.readouterr().out
    assert (
        f"you already registered {old.pubkey()}; registering again replaces it, "
        f"so tell the instructor if {old.pubkey()} was already funded"
    ) in out
    assert registry.calls == []  # stopped before a challenge was spent

    assert wallet.main(["register", "--replace"], transport=registry) == 0
    out = capsys.readouterr().out
    assert f"registered {new.pubkey()}" in out
    assert registry.calls[1][3]["address"] == str(new.pubkey())


def test_the_server_saying_replaced_prints_the_warning(
    home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Registered earlier from another machine: no local record, so the server's word is
    the only warning there can be."""
    created(home, capsys)
    assert wallet.main(["register"], transport=FakeRegistry(replaced=True)) == 0
    assert (
        "this replaced your earlier address; tell the instructor, "
        "in case the old one was already funded"
    ) in capsys.readouterr().out


def test_the_registration_record_holds_no_key(
    home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    key, _ = created(home, capsys)
    wallet.main(["register"], transport=FakeRegistry())
    record = (home / ".config" / "dev3pack" / "registered-wallet.json").read_text()
    assert json.loads(record)["address"] == str(key.pubkey())
    assert GECKO_KEY not in record and str(key) not in record
