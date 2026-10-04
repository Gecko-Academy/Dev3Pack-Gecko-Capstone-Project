"""Refuse a commit that carries a key. Stdlib only; runs as the pre-commit hook and in CI.

    python3 scripts/scan_secrets.py            # every tracked file
    python3 scripts/scan_secrets.py --staged   # what is about to be committed (the hook)

It looks for what a Solana key actually looks like on disk, not for the word "key":

* a JSON array of exactly 64 small integers (the Solana CLI keypair format);
* a file whose name says it is a keypair (`*keypair*.json`, `id.json`, `devnet-*.json`,
  `mainnet-*.json`, `friday-*.json`, `*.pem`, `*.key`);
* a PEM private key block;
* an assignment of a secret-looking name (`PRIVATE_KEY=`, `SECRET_KEY=`, `SEED_PHRASE=`,
  `MNEMONIC=`) to a long value.

It prints the file, the line and WHICH rule matched. It never prints the match itself.
Addresses and transaction signatures are public and are not flagged.
"""

from __future__ import annotations

import argparse
import fnmatch
import re
import subprocess
import sys
from pathlib import Path

KEYPAIR_ARRAY = re.compile(r"\[\s*(?:\d{1,3}\s*,\s*){63}\d{1,3}\s*\]")
PEM = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")
ASSIGNED = re.compile(
    r"(?i)\b(private_key|secret_key|seed_phrase|mnemonic)\b\s*[:=]\s*[\"']?[^\s\"']{16,}"
)
NAMES = [
    "*keypair*.json",
    "id.json",
    "devnet-*.json",
    "mainnet-*.json",  # mainnet-wallet.json: Friday's real-money key
    "friday-*.json",
    "*.pem",
    "*.key",
]


def findings_in(name: str, text: str) -> list[str]:
    found = []
    base = Path(name).name
    if any(fnmatch.fnmatch(base, pattern) for pattern in NAMES):
        found.append(f"{name}: the file name is a keypair's")
    for number, line in enumerate(text.splitlines(), 1):
        if PEM.search(line):
            found.append(f"{name}:{number}: a PEM private key block")
        if ASSIGNED.search(line):
            found.append(f"{name}:{number}: a secret-looking name assigned a value")
    for match in KEYPAIR_ARRAY.finditer(text):
        numbers = [int(n) for n in re.findall(r"\d+", match.group(0))]
        if all(0 <= n <= 255 for n in numbers):
            line = text.count("\n", 0, match.start()) + 1
            found.append(f"{name}:{line}: a 64-byte array, the shape of a Solana keypair")
    return found


def _git(*args: str) -> str:
    # errors="ignore", like the unstaged path below: a staged image or other binary
    # is scanned on its readable bytes instead of crashing the hook (issue #12).
    return subprocess.run(
        ["git", *args], capture_output=True, text=True, errors="ignore", check=True
    ).stdout


def files(staged: bool) -> list[tuple[str, str]]:
    if staged:
        names = _git("diff", "--cached", "--name-only", "--diff-filter=ACMR").split()
        return [(n, _git("show", f":{n}")) for n in names]
    out = []
    for name in _git("ls-files").split("\n"):
        path = Path(name)
        if name and path.is_file():
            out.append((name, path.read_text(encoding="utf-8", errors="ignore")))
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--staged", action="store_true", help="scan the staged changes only")
    args = parser.parse_args()
    found = []
    scanned = files(args.staged)
    for name, text in scanned:
        found += findings_in(name, text)
    if found:
        print("REFUSING: this looks like a key. Keys live in ~/.config/dev3pack/, never here.")
        for line in found:
            print(f"  {line}")
        print("If it is really not a key, rename or reshape it; do not skip this check.")
        return 1
    print(f"key scan: {len(scanned)} files, nothing found")
    return 0


if __name__ == "__main__":
    sys.exit(main())
