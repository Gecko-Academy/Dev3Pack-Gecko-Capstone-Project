"""Project 01 self-check: read the responses you saved and say what they show.

    python3 projects/01-read-the-menu/check.py               # score the saved responses
    python3 projects/01-read-the-menu/check.py --dir <path>  # score responses saved elsewhere
    python3 projects/01-read-the-menu/check.py show <file>   # print one saved response, readable
    python3 projects/01-read-the-menu/check.py address       # print a throwaway buyer address

Standard library only. No network: this script reads files you already saved and calls
nothing. The score it prints is LOCAL. It is not sent anywhere, and it does not reach the
leaderboard or any grader.

A saved file may be any of three shapes, and all three are read the same way:
  1. the raw curl output, as server-sent events (lines starting "data: ");
  2. a JSON-RPC envelope, {"jsonrpc": "2.0", "result": {"content": [{"text": ...}]}};
  3. the tool's own JSON result, copied out of an MCP client.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
LET_ME_BUY = "BUYuxRfhCMWavaUWxhGtPP3ksKEDZxCD5gzknk3JfAya"
B58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
ADDRESS = re.compile(r"^[1-9A-HJ-NP-Za-km-z]{32,44}$")

# Refusal codes that come from the REQUEST (what you asked for), as opposed to the chain.
REQUEST_REFUSALS = {
    "product-unknown",
    "store-unknown",
    "argument-invalid",
    "signer-required",
    "network-not-asserted",
}
# What an honest prepare can return: bytes that passed, or a refusal about the wallet.
PREPARE_REFUSALS_ACCEPTED = {"receipt-failed", "signer-required"}


class ResponseError(Exception):
    """A saved file is missing, empty, or not a tool result."""


# ---------------------------------------------------------------- reading a saved file


def _unwrap(value: Any) -> Any:
    """Peel a JSON-RPC envelope down to the tool's own result dict."""
    if isinstance(value, dict) and "jsonrpc" in value:
        if "error" in value:
            err = value["error"]
            message = err.get("message") if isinstance(err, dict) else err
            raise ResponseError(f"the server answered with a JSON-RPC error: {message}")
        value = value.get("result")
    if isinstance(value, dict) and isinstance(value.get("structuredContent"), dict):
        return value["structuredContent"]
    if isinstance(value, dict) and isinstance(value.get("content"), list):
        for part in value["content"]:
            if isinstance(part, dict) and part.get("type") == "text":
                try:
                    return json.loads(part["text"])
                except (KeyError, json.JSONDecodeError) as exc:
                    raise ResponseError(
                        "the tool answered with text that is not JSON"
                    ) from exc
    return value


def load_result(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ResponseError(f"{path.name} not found in {path.parent}")
    raw = path.read_text(encoding="utf-8").strip()
    if not raw:
        raise ResponseError(f"{path.name} is empty")
    data_lines = [
        line[len("data:") :].strip() for line in raw.splitlines() if line.startswith("data:")
    ]
    text = data_lines[-1] if data_lines else raw
    if "Missing session ID" in text:
        raise ResponseError(
            f"{path.name} holds 'Missing session ID': the handshake did not run first"
        )
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ResponseError(f"{path.name} is not JSON ({exc.msg})") from exc
    result = _unwrap(parsed)
    if not isinstance(result, dict):
        raise ResponseError(f"{path.name} does not hold a tool result object")
    return result


# ---------------------------------------------------------------- the checks


class Report:
    def __init__(self) -> None:
        self.lines: list[tuple[bool, str, str]] = []
        self.notes: list[str] = []

    def add(self, ok: bool, name: str, detail: str) -> None:
        self.lines.append((ok, name, detail))

    def note(self, text: str) -> None:
        """Worth knowing, not scored."""
        self.notes.append(text)

    def print(self) -> int:
        width = max(len(name) for _, name, _ in self.lines)
        for ok, name, detail in self.lines:
            mark = "PASS" if ok else "FAIL"
            print(f"  {mark}  {name.ljust(width)}  {detail}")
        for text in self.notes:
            print(f"  note  {text}")
        passed = sum(1 for ok, _, _ in self.lines if ok)
        total = len(self.lines)
        print()
        print(f"local score: {passed}/{total}")
        print(
            "This score is local. It is not sent anywhere and it does not reach the "
            "leaderboard. Project 01 is not marked."
        )
        return 0 if passed == total else 1


def _menu_names(menu: dict[str, Any] | None) -> set[str]:
    if not menu:
        return set()
    return {
        str(product.get("name", "")).strip().lower()
        for store in menu.get("stores", [])
        for product in store.get("products", [])
        if isinstance(product, dict)
    }


def _no_menu(report: Report, why: str) -> None:
    report.add(False, "menu saved", why)
    report.add(False, "prices are whole units", "no menu to read")
    report.add(False, "mint and token program", "no menu to read")


def check_menu(report: Report, directory: Path) -> dict[str, Any] | None:
    try:
        menu = load_result(directory / "list_stores.json")
    except ResponseError as exc:
        _no_menu(report, str(exc))
        return None

    if "error" in menu:
        _no_menu(report, f"the tool answered with an error: {menu['error']}")
        return None
    stores = menu.get("stores")
    if not isinstance(stores, list) or not stores:
        _no_menu(
            report,
            "no stores in list_stores.json. A filter that matched nothing returns an "
            "empty list; call again without it",
        )
        return None
    names = ", ".join(str(s.get("store")) for s in stores[:3])
    report.add(True, "menu saved", f"{len(stores)} store(s): {names}")

    products = [p for s in stores for p in s.get("products", []) if isinstance(p, dict)]
    bad_price = [
        p.get("name")
        for p in products
        if not isinstance(p.get("price_raw"), int)
        or isinstance(p.get("price_raw"), bool)
        or not isinstance(p.get("decimals"), int)
    ]
    if products and not bad_price:
        sample = products[0]
        report.add(
            True,
            "prices are whole units",
            f"e.g. {sample.get('name')}: price_raw {sample['price_raw']}, "
            f"decimals {sample['decimals']}",
        )
    else:
        report.add(
            False,
            "prices are whole units",
            f"price_raw or decimals missing or not whole numbers for: {bad_price or 'every product'}",
        )

    bad_mint = [
        p.get("name")
        for p in products
        if not ADDRESS.match(str(p.get("mint", "")))
        or not isinstance(p.get("token_program"), dict)
    ]
    if products and not bad_mint:
        report.add(
            True,
            "mint and token program",
            "every product carries a mint address and a token_program; match on those, "
            "never on mint_note",
        )
    else:
        report.add(
            False,
            "mint and token program",
            f"mint address or token_program missing for: {bad_mint or 'every product'}",
        )
    return menu


def check_prepare(report: Report, directory: Path, menu: dict[str, Any] | None) -> None:
    try:
        prep = load_result(directory / "prepare.json")
    except ResponseError as exc:
        report.add(False, "prepare saved", str(exc))
        report.add(False, "nothing signed", "no prepare response to read")
        return

    if "error" in prep:
        report.add(
            False,
            "prepare saved",
            f"transport error, not an answer: {prep['error']}. Run the call again",
        )
        report.add(False, "nothing signed", "no prepare response to read")
        return

    if prep.get("refused") is False:
        expires = prep.get("expires") or {}
        built_by = (prep.get("instruction") or {}).get("built_by")
        blocks = expires.get("blocks_remaining")
        missing = [
            name
            for name, value in (
                ("status", prep.get("status")),
                ("expires.blocks_remaining", blocks),
                ("instruction.built_by", built_by),
            )
            if value is None
        ]
        if prep.get("status") == "pass" and not missing:
            has_effects = "effects" in prep
            report.add(
                True,
                "prepare saved",
                f"status pass, {blocks} blocks left when prepared, built_by {built_by}"
                + ("" if has_effects else " (no `effects` in this result)"),
            )
        else:
            report.add(False, "prepare saved", f"prepared, but missing: {missing}")
    elif prep.get("refused") is True:
        code = prep.get("code")
        if code in PREPARE_REFUSALS_ACCEPTED:
            report.add(
                True,
                "prepare saved",
                f"refused with {code}: the order resolved and the wallet cannot pay. "
                "That is the expected answer for an empty wallet",
            )
        else:
            report.add(
                False,
                "prepare saved",
                f"refused with {code}. prepare.json should be a real order with your "
                "buyer address. Save this one as refusal.json instead",
            )
    else:
        report.add(False, "prepare saved", "not a prepare_purchase result (no `refused` field)")

    transaction = prep.get("transaction")
    signed = transaction.get("signed") if isinstance(transaction, dict) else None
    if signed is True:
        report.add(False, "nothing signed", "transaction.signed is true. Nothing in this project signs")
    else:
        report.add(
            True,
            "nothing signed",
            "unsigned bytes" if transaction else "no transaction returned, so nothing to sign",
        )

    product = (prep.get("args") or {}).get("product_name") or (prep.get("order") or {}).get(
        "product"
    )
    if product and menu:
        on_menu = str(product).strip().lower() in _menu_names(menu)
        report.note(
            f"prepared item {product!r} "
            + ("appears in list_stores.json" if on_menu else "is NOT in the menu you saved")
        )


def check_refusal(report: Report, directory: Path) -> None:
    try:
        refusal = load_result(directory / "refusal.json")
    except ResponseError as exc:
        report.add(False, "refusal saved", str(exc))
        return
    if refusal.get("refused") is not True:
        report.add(
            False,
            "refusal saved",
            "refusal.json is not a refusal. Ask for a product the store does not sell, "
            "or leave out `buyer`",
        )
        return
    code, reason = refusal.get("code"), refusal.get("reason")
    if not code or not reason:
        report.add(False, "refusal saved", "a refusal needs both a `code` and a `reason`")
        return
    kind = "about your request" if code in REQUEST_REFUSALS else "about the chain"
    extra = ""
    if code == "product-unknown" and refusal.get("products"):
        extra = f"; it also lists the {len(refusal['products'])} real products"
    report.add(True, "refusal saved", f"code {code} ({kind}){extra}")


def check_telegram(report: Report, directory: Path, menu: dict[str, Any] | None) -> None:
    path = directory / "telegram.txt"
    if not path.is_file() or not path.read_text(encoding="utf-8").strip():
        report.add(False, "telegram compared", "paste the bot's reply into responses/telegram.txt")
        return
    text = path.read_text(encoding="utf-8").lower()
    shared = sorted(name for name in _menu_names(menu) if name and name in text)
    if shared:
        report.add(True, "telegram compared", f"same products in both: {', '.join(shared[:3])}")
    else:
        report.add(
            False,
            "telegram compared",
            "no product name from list_stores.json appears in telegram.txt. Did you ask "
            "the bot about the same store?",
        )


def check_no_secrets(report: Report, directory: Path) -> None:
    # A Solana keypair file is a JSON array of 64 small integers. It never belongs here.
    keypair = re.compile(r"\[\s*(\d{1,3}\s*,\s*){63}\d{1,3}\s*\]")
    offenders = []
    for path in sorted(directory.glob("*")):
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if "PRIVATE KEY" in text or keypair.search(text):
            offenders.append(path.name)
    if offenders:
        report.add(False, "no secret in responses", f"remove it now: {', '.join(offenders)}")
    else:
        report.add(True, "no secret in responses", "no private key or keypair array found")


# ---------------------------------------------------------------- the helpers


def b58encode(raw: bytes) -> str:
    value = int.from_bytes(raw, "big")
    out = ""
    while value:
        value, digit = divmod(value, 58)
        out = B58[digit] + out
    return "1" * (len(raw) - len(raw.lstrip(b"\x00"))) + out


def throwaway_address() -> str:
    """32 random bytes, written as an address. No private key exists for it, anywhere."""
    return b58encode(os.urandom(32))


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Project 01 local self-check (no network).")
    parser.add_argument("command", nargs="?", default="check", choices=["check", "show", "address"])
    parser.add_argument("file", nargs="?", help="for `show`: the saved response to print")
    parser.add_argument("--dir", default=str(HERE / "responses"), help="where the responses are")
    args = parser.parse_args(argv)

    if args.command == "address":
        print(throwaway_address())
        print(
            "\nA throwaway buyer address. Nobody holds a key for it, so it can never sign "
            "and never spend.\nIt is empty on mainnet. Use it to see what an empty wallet "
            "gets back.",
            file=sys.stderr,
        )
        return 0

    if args.command == "show":
        if not args.file:
            parser.error("show needs a file, e.g. responses/list_stores.json")
        try:
            print(json.dumps(load_result(Path(args.file)), indent=2))
        except ResponseError as exc:
            print(f"cannot read it: {exc}", file=sys.stderr)
            return 1
        return 0

    directory = Path(args.dir)
    print(f"project 01 self-check, reading {directory}\n")
    report = Report()
    menu = check_menu(report, directory)
    check_prepare(report, directory, menu)
    check_refusal(report, directory)
    check_telegram(report, directory, menu)
    check_no_secrets(report, directory)
    return report.print()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
