"""`uv run buyer "<what you want>" --recorded | --devnet`

--recorded   offline: Gecko's answers and the ledger reads come from fixtures/. No key,
             no network, no money. `GECKO_SOURCE=recorded` does the same.
--devnet     live: the hosted Gecko MCP, your devnet key, devnet SOL and your own token.
--mainnet    Friday only, with your own mainnet wallet (scripts/mainnet_wallet.py), funded
             by the founder with three espressos. --mainnet-budget-raw defaults to
             300000, and the signer refuses any cap or purchase above that.

--cases      run the five use cases (and the trap) from fixtures/cases/, and compare
             each outcome with what the fixture expects.
--cards      run the four Friday failure cards from fixtures/cards/.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .agent import Outcome, Run, execute
from .chain import DEVNET_RPC
from .intent import Context
from .ledger import LiveChain, RecordedChain, RecordingChain
from .mcp_client import HostedGecko, RecordedGecko, RecordingGecko, load_fixture
from .signer import CONFIG_DIR, MAINNET_CAP_RAW, KeypairSigner, RecordedSigner, mainnet_wallet_path

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "fixtures"
MAINNET_RPC = "https://api.mainnet-beta.solana.com"
MAINNET_USDC = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
DEFAULT_BUDGET_RAW = 2_000_000


def _devnet_config() -> dict[str, Any]:
    path = CONFIG_DIR / "devnet.json"
    return json.loads(path.read_text()) if path.is_file() else {}


def _default_store() -> str | None:
    path = ROOT / "store" / "store.json"
    if path.is_file():
        return json.loads(path.read_text()).get("store")
    return None


def _fixtures(group: str) -> list[Path]:
    return sorted((FIXTURES / group).glob("*.json"))


def _fixture_for(ask: str) -> dict[str, Any]:
    wanted = ask.strip().lower()
    for group in ("cases", "cards"):
        for path in _fixtures(group):
            fixture = load_fixture(path)
            if fixture.get("ask", "").strip().lower() == wanted:
                return fixture
    asks = [load_fixture(p)["ask"] for p in _fixtures("cases")]
    raise SystemExit(
        f"no recorded answer for {ask!r}. Recorded asks: " + "; ".join(repr(a) for a in asks)
    )


def recorded_run(fixture: dict[str, Any], out: Path, card: str | None = None) -> Run:
    ledger = RecordedChain(fixture["ledger"])
    ctx = fixture["context"]
    return Run(
        ask=fixture["ask"],
        context=Context(**ctx),
        gecko=RecordedGecko(fixture),
        chain=ledger,
        signer=RecordedSigner(fixture, ledger),
        out=out,
        source="recorded",
        card=card or fixture.get("card"),
    )


class _RecordingSigner:
    def __init__(self, inner: KeypairSigner) -> None:
        self.inner, self.cluster, self.address = inner, inner.cluster, inner.address
        self.signed: str | None = None

    def sign(self, prepared: Any) -> str:
        self.signed = self.inner.sign(prepared)
        return self.signed


def live_run(args: argparse.Namespace, ask: str, context_overrides: dict[str, Any]) -> Run:
    if args.mainnet:
        cluster, rpc = "mainnet", os.environ.get("GECKO_MAINNET_RPC", MAINNET_RPC)
        # One path, never an override: the only mainnet key is the one `mainnet_wallet.py
        # create` made on this machine and registered with Gecko.
        key = str(mainnet_wallet_path())
        if not Path(key).is_file():
            raise SystemExit(
                f"--mainnet needs your wallet at {key}: "
                "run `uv run python scripts/mainnet_wallet.py create`, then register it"
            )
        if args.mainnet_budget_raw is None:
            args.mainnet_budget_raw = MAINNET_CAP_RAW
        pay_mint = args.mint or MAINNET_USDC
    else:
        cluster, rpc = "devnet", os.environ.get("GECKO_DEVNET_RPC", DEVNET_RPC)
        config = _devnet_config()
        key = os.environ.get("GECKO_DEVNET_KEYPAIR") or config.get("buyer", {}).get("keypair")
        if not key:
            raise SystemExit(
                "no devnet key: run `uv run python scripts/devnet_setup.py`, "
                "or set GECKO_DEVNET_KEYPAIR to a keypair file outside this repo"
            )
        pay_mint = args.mint or os.environ.get("GECKO_PAY_MINT") or config.get("mint")
    ledger = LiveChain(cluster, rpc)
    signer = KeypairSigner(
        Path(key), cluster, ledger, args.mainnet_budget_raw if args.mainnet else None
    )
    context = {
        "store": args.store or _default_store(),
        "network": cluster,
        "buyer": signer.address,
        "pay_mint": pay_mint,
        "budget_raw": args.budget_raw if args.budget_raw is not None else DEFAULT_BUDGET_RAW,
    }
    context.update({k: v for k, v in context_overrides.items() if k not in ("buyer", "network")})
    if not context["store"]:
        raise SystemExit("which store? pass --store, or fill store/store.json")
    if not context["pay_mint"]:
        raise SystemExit("which mint do you pay with? pass --mint <address>")
    gecko: Any = HostedGecko()
    chain: Any = ledger
    if args.record:
        gecko, chain, signer = (
            RecordingGecko(gecko),
            RecordingChain(ledger),
            _RecordingSigner(signer),
        )  # type: ignore[assignment]
    return Run(
        ask=ask,
        context=Context(**context),
        gecko=gecko,
        chain=chain,
        signer=signer,
        out=Path(args.out),
        source=cluster,
        card=args.card,
    )


def _save_recording(run: Run, outcome: Outcome, path: Path) -> None:
    fixture = {
        "ask": run.ask,
        "context": asdict(run.context),
        "calls": run.gecko.calls,  # type: ignore[attr-defined]
        "signed_transaction": getattr(run.signer, "signed", None),
        "ledger": run.chain.to_fixture(),  # type: ignore[attr-defined]
        "expected": _expected_of(outcome),
        "note": "recorded from a real run; edit `expected` to say what SHOULD happen",
    }
    if run.card:
        fixture["card"] = run.card
    if run.card == "tampered" and "verify_signed_transaction" in fixture["calls"]:
        # The only verify this run made was over the tampered bytes.
        fixture["calls"]["verify_signed_transaction:other"] = fixture["calls"].pop(
            "verify_signed_transaction"
        )
    expires = (run.answer or {}).get("expires", {})
    if "current_block_height" in expires:
        # Replays start where the chain was when the bytes were prepared.
        fixture["ledger"]["block_height"] = expires["current_block_height"]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(fixture, indent=2) + "\n", encoding="utf-8")


def _expected_of(outcome: Outcome) -> dict[str, Any]:
    if outcome.kind == "refused" and outcome.refusal:
        return {"outcome": "refused", "field": outcome.refusal.field}
    if outcome.kind == "gecko-refused":
        return {"outcome": "gecko-refused", "code": outcome.gecko_code}
    return {"outcome": outcome.kind}


def matches(expected: dict[str, Any], outcome: Outcome) -> bool:
    if outcome.kind != expected.get("outcome"):
        return False
    if "field" in expected:
        # A list means any of these fields is a fair place to refuse (the trap: the name
        # can be refused as a product, or its price refused as over budget).
        allowed = expected["field"] if isinstance(expected["field"], list) else [expected["field"]]
        return bool(outcome.refusal and outcome.refusal.field in allowed)
    if "code" in expected:
        return outcome.gecko_code == expected["code"]
    return True


def _expected_line(expected: dict[str, Any]) -> str:
    if expected.get("outcome") == "refused":
        allowed = expected["field"] if isinstance(expected["field"], list) else [expected["field"]]
        text = "refuse on " + " or ".join(f"`{f}`" for f in allowed)
        return f"{text}: {expected['shape']}" if expected.get("shape") else text
    return str(expected.get("outcome"))


def run_group(group: str, args: argparse.Namespace) -> int:
    rows = []
    for path in _fixtures(group):
        fixture = load_fixture(path)
        print(f"\n{path.stem}: {fixture['ask']!r}")
        if args.devnet or args.mainnet:
            run = live_run(args, fixture["ask"], fixture["context"])
            run.card = run.card or fixture.get("card")
        else:
            run = recorded_run(fixture, Path(args.out))
        outcome = execute(run)
        expected = fixture.get("expected", {})
        ok = matches(expected, outcome)
        print(f"  expected: {_expected_line(expected)}  ->  {'MATCH' if ok else 'not yet'}")
        rows.append(
            {
                "source": run.source,
                "case": path.stem,
                "ask": fixture["ask"],
                "expected": expected,
                "match": ok,
                "outcome": outcome.to_json(),
            }
        )
    hits = sum(r["match"] for r in rows)
    print(f"\n{hits}/{len(rows)} {group} match what the fixtures expect")
    if args.json:
        Path(args.json).write_text(json.dumps(rows, indent=2, default=str) + "\n")
    return 0 if hits == len(rows) else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="buyer", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("ask", nargs="?", help='what you want, in plain words: "one espresso"')
    lane = parser.add_mutually_exclusive_group()
    lane.add_argument("--recorded", action="store_true", help="offline, from fixtures/")
    lane.add_argument("--devnet", action="store_true", help="live on devnet with your key")
    lane.add_argument("--mainnet", action="store_true", help="Friday only, your capped wallet")
    parser.add_argument("--cases", action="store_true", help="run fixtures/cases/")
    parser.add_argument("--cards", action="store_true", help="run fixtures/cards/")
    parser.add_argument("--store", help="store name (default: store/store.json)")
    parser.add_argument("--mint", help="the mint you pay with, as an address")
    parser.add_argument("--budget-raw", type=int, help=f"default {DEFAULT_BUDGET_RAW}")
    parser.add_argument(
        "--mainnet-budget-raw",
        type=int,
        help=f"Friday: the most one signature may spend (default and ceiling {MAINNET_CAP_RAW})",
    )
    parser.add_argument("--card", choices=["tampered", "stale"], help="inject a Friday card")
    parser.add_argument("--record", help="save this live run as a fixture at this path")
    parser.add_argument("--out", help="where intents/, receipts/, refusals/ go")
    parser.add_argument("--json", help="write the case table as JSON here")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not (args.devnet or args.mainnet):
        args.recorded = True
    # The rollback switch: GECKO_SOURCE=recorded wins over any live flag.
    if os.environ.get("GECKO_SOURCE") == "recorded":
        args.devnet = args.mainnet = False
        args.recorded = True
    if args.out is None:
        # Recorded runs never mix with real evidence: they go to .recorded/ (gitignored).
        args.out = str(ROOT / ".recorded") if args.recorded else str(ROOT)

    if args.cases or args.cards:
        return run_group("cases" if args.cases else "cards", args)
    if not args.ask:
        parser.error('say what you want: uv run buyer "one espresso" --recorded')

    if args.recorded:
        run = recorded_run(_fixture_for(args.ask), Path(args.out), args.card)
    else:
        run = live_run(args, args.ask, {})
    print(f'{run.context.store}  "{run.ask}"  ({run.source})')
    outcome = execute(run)
    if args.record and not args.recorded:
        _save_recording(run, outcome, Path(args.record))
        print(f"  recorded to {args.record}")
    return {"landed": 0, "refused": 1, "gecko-refused": 1, "not-written": 2}.get(outcome.kind, 3)


if __name__ == "__main__":
    sys.exit(main())
