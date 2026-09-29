"""Friday: your own mainnet wallet, made on this machine, registered with Gecko by address.

    uv run python scripts/mainnet_wallet.py create     # once: a new key, address printed
    uv run python scripts/mainnet_wallet.py register   # prove you hold it, with your Gecko key
    uv run python scripts/mainnet_wallet.py show       # address, mainnet SOL and USDC

THIS IS MAINNET. REAL MONEY. The founder funds a registered address with three espressos
(300000 raw USDC, 6 decimals) and about 0.0094 SOL for fees, and nothing more.

`create` writes ~/.config/dev3pack/mainnet-wallet.json (mode 600, outside this repo) and
refuses to overwrite one that exists. The key never leaves this machine: `register` sends
the address and a signature over a one-time challenge, never the key.

The key is used for exactly two things: signing that challenge, and Friday's purchases
through `uv run buyer ... --mainnet`, whose signer refuses anything above 300000 raw.

`register` reads your Gecko key from GECKO_API_KEY, or asks for it without echoing. It is
never an argument, never written to a file and never printed.

Each `register` run fetches a fresh one-time challenge and never retries on its own: a
failed attempt spends its challenge, and the registry allows 120 requests an hour per IP.
Registering a different address replaces the old one, which may already be funded: a
second address from this machine is refused until you pass `--replace`, and the address
you registered is remembered (public, no key) in ~/.config/dev3pack/registered-wallet.json.

`show` is read-only: it asks a public mainnet RPC for two balances and signs nothing.
"""

from __future__ import annotations

import argparse
import getpass
import json
import os
import sys
import urllib.error
import urllib.request
from collections.abc import Callable
from pathlib import Path
from typing import Any

from solders.keypair import Keypair
from solders.pubkey import Pubkey

from buyer import chain
from buyer.cli import MAINNET_RPC, MAINNET_USDC
from buyer.letmebuy import token_account
from buyer.signer import (
    MAINNET_CAP_RAW,
    KeyLocationError,
    inside_git_repo,
    load_keypair,
    mainnet_wallet_path,
)

GECKO = "https://mcp.geckovision.tech"
COHORT = "2026-09"
USDC_DECIMALS = 6
LAMPORTS_PER_SOL = 1_000_000_000

#: (method, url, headers, JSON body or None) -> (HTTP status, parsed JSON body).
#: Injected in tests, so nothing there reaches the registry.
Transport = Callable[[str, str, dict[str, str], dict[str, Any] | None], tuple[int, Any]]


def http(
    method: str, url: str, headers: dict[str, str], body: dict[str, Any] | None
) -> tuple[int, Any]:
    data = None if body is None else json.dumps(body).encode()
    request = urllib.request.Request(
        url,
        data,
        {**headers, "content-type": "application/json", "user-agent": "dev3pack-gecko-buyer"},
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            status, raw = response.status, response.read()
    except urllib.error.HTTPError as exc:
        # An error status still carries the server's {"error", "code"}: read it, do not raise.
        status, raw = exc.code, exc.read()
    try:
        return status, json.loads(raw or b"null")
    except ValueError:
        return status, None


def create(path: Path) -> int:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if inside_git_repo(path):
        print(f"refusing: {path.parent} is inside a git repository. Keys never live in a repo.")
        return 1
    key = Keypair()
    try:
        # O_EXCL: if a wallet is already there, fail rather than replace a funded key.
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        print(f"refusing: {path} already exists, and it may hold money. Nothing was changed.")
        print("  `show` prints its address. Never delete it while it holds a balance.")
        return 1
    with os.fdopen(fd, "w") as handle:
        json.dump(list(bytes(key)), handle)
    print(f"made     {path}  (mode 600, never commit it, never share it)")
    print(f"address  {key.pubkey()}")
    print("\nNext: `gecko login`, then `uv run python scripts/mainnet_wallet.py register`.")
    return 0


def _wallet(path: Path) -> Keypair | None:
    try:
        return load_keypair(path)
    except KeyLocationError as exc:
        print(f"refusing: {exc}")
        if not path.exists():
            print("  make it first: uv run python scripts/mainnet_wallet.py create")
        return None


def _gecko_key() -> str:
    if os.environ.get("GECKO_API_KEY"):
        return os.environ["GECKO_API_KEY"]
    if not sys.stdin.isatty():
        # Without a terminal, getpass falls back to an echoing prompt. Refuse instead.
        return ""
    try:
        return getpass.getpass("Gecko key (not echoed): ")
    except (EOFError, KeyboardInterrupt):
        return ""


def _refusal(status: int, body: Any, secret: str) -> str:
    if isinstance(body, dict) and body.get("error"):
        text = str(body["error"])
        code = body.get("code")
        line = f"{text} ({code}, HTTP {status})" if code else f"{text} (HTTP {status})"
    elif status == 429:
        line = "too many requests (HTTP 429)"
    elif status == 503:
        line = "registration is not open yet (HTTP 503); ask the instructor"
    else:
        line = f"unexpected answer from Gecko (HTTP {status})"
    if status == 429:
        # Do not loop: each attempt costs a request against the per-IP hourly limit.
        line += "; wait a minute and run register again"
    # A server should never echo the key back; if one ever did, it still is not printed.
    return line.replace(secret, "<redacted>") if secret else line


def _record_path(path: Path) -> Path:
    # Public data only (address, account): lets `register` warn BEFORE it replaces an
    # address the founder may already have funded. The registry has no read endpoint.
    return path.parent / "registered-wallet.json"


def _registered_before(path: Path) -> str | None:
    try:
        return str(json.loads(_record_path(path).read_text())["address"])
    except (OSError, ValueError, KeyError, TypeError):
        return None


def _replace_warning(old: str) -> str:
    return (
        f"you already registered {old}; registering again replaces it, "
        f"so tell the instructor if {old} was already funded"
    )


def register(
    path: Path,
    gecko: str,
    transport: Transport,
    secret: str | None = None,
    replace: bool = False,
) -> int:
    key = _wallet(path)
    if key is None:
        return 1
    address = str(key.pubkey())
    old = _registered_before(path)
    if old and old != address:
        print(f"warning: {_replace_warning(old)}.")
        if not replace:
            # Checked before any request: no challenge is spent on a registration we stop.
            print("Nothing was sent. If you mean it, run `register --replace`.")
            return 1
    secret = secret if secret is not None else _gecko_key()
    if not secret.strip():
        print("refusing: no Gecko key. Set GECKO_API_KEY, or paste it at the prompt.")
        return 1
    headers = {"authorization": f"Bearer {secret.strip()}"}

    # A challenge is single-use and the server consumes it BEFORE checking the signature, so
    # any failed POST burns it. Every run fetches a fresh one; nothing here retries or keeps one.
    status, body = transport(
        "GET", f"{gecko}/registry/class-wallet/challenge?cohort={COHORT}", headers, None
    )
    if status != 200 or not isinstance(body, dict) or not body.get("challenge"):
        print(f"not registered: {_refusal(status, body, secret)}")
        return 1
    challenge = str(body["challenge"])
    # The signature is over the challenge's exact UTF-8 bytes: it proves this machine holds
    # the key behind `address`, and it cannot move anything (it is not a transaction).
    signature = key.sign_message(challenge.encode("utf-8"))

    status, body = transport(
        "POST",
        f"{gecko}/registry/class-wallet",
        headers,
        {"cohort": COHORT, "address": address, "challenge": challenge, "signature": str(signature)},
    )
    if status not in (200, 201) or not isinstance(body, dict) or body.get("error"):
        print(f"not registered: {_refusal(status, body, secret)}")
        return 1
    print(f"registered {body.get('address', address)} for {body.get('account')}")
    _record_path(path).write_text(
        json.dumps({"address": address, "account": body.get("account"), "cohort": COHORT}) + "\n"
    )
    if body.get("replaced"):
        # The server says an earlier address was replaced (it may have been registered from
        # another machine, so the local record cannot always warn first).
        print(
            "warning: this replaced your earlier address; tell the instructor, "
            "in case the old one was already funded"
        )
    print("Next: wait for the instructor to fund it, then `... mainnet_wallet.py show`.")
    return 0


def show(path: Path, rpc: str) -> int:
    key = _wallet(path)
    if key is None:
        return 1
    owner: Pubkey = key.pubkey()
    print(f"address  {owner}")
    try:
        chain.assert_cluster(rpc, "mainnet")
        lamports = chain.lamports(rpc, owner)
        usdc_raw = chain.token_balance_raw(
            rpc, token_account(owner, Pubkey.from_string(MAINNET_USDC))
        )
    except (chain.ChainError, chain.WrongCluster, OSError) as exc:
        print(f"could not read mainnet: {str(exc)[:120]}")
        return 1
    print(f"SOL      {lamports / LAMPORTS_PER_SOL:.6f}  ({lamports} lamports)")
    print(f"USDC     {usdc_raw / 10**USDC_DECIMALS:.6f}  ({usdc_raw} raw)")
    print(f"explorer {chain.explorer(str(owner), 'mainnet', 'address')}")
    if usdc_raw:
        print(
            f'\nFriday: uv run buyer "one espresso" --mainnet --store geckocoffee '
            f"(signs at most {MAINNET_CAP_RAW} raw)"
        )
    return 0


def main(argv: list[str] | None = None, transport: Transport = http) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("command", choices=["create", "register", "show"])
    parser.add_argument(
        "--replace",
        action="store_true",
        help="register this wallet even though another address was registered from here",
    )
    parser.add_argument("--rpc", default=os.environ.get("GECKO_MAINNET_RPC", MAINNET_RPC))
    args = parser.parse_args(argv)

    path = mainnet_wallet_path().expanduser().resolve()
    if args.command == "create":
        return create(path)
    if args.command == "register":
        return register(path, GECKO, transport, replace=args.replace)
    return show(path, args.rpc)


if __name__ == "__main__":
    sys.exit(main())
