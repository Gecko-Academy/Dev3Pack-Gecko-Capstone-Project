#!/usr/bin/env python3
"""Grade several candidate APIs at once, then refuse the ones that are not ready.

Fan out: one lane per candidate, all running together, none waiting on another.
Verify: one stage that reads every lane's artifact and decides.

Standard library only. The work is done by the gecko CLI, which needs no key and,
for a local spec file, no network.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_SPECS = sorted((HERE / "specs").glob("*.json"))
GECKO = shlex.split(os.environ.get("GECKO", "npx -y @geckovision/gecko"))
LANE_TIMEOUT = int(os.environ.get("SURVEY_TIMEOUT", "300"))


@dataclass
class Lane:
    """One candidate API, and everything the verify stage needs to judge it."""

    ref: str
    grade: str = "?"
    score: int = 0
    blocking: list[str] = field(default_factory=list)
    passed: int = 0
    total: int = 0
    error: str = ""

    @property
    def label(self) -> str:
        """Short name for the table. A URL shows its host, so two openapi.json URLs differ."""
        if "://" in self.ref:
            return self.ref.split("://", 1)[1].split("/", 1)[0]
        return Path(self.ref).name

    @property
    def slug(self) -> str:
        """Artifact filename. The hash is load-bearing: two long absolute paths that
        share a prefix truncate to the same name, and then one lane reads the other
        lane's report and reports its grade."""
        stem = re.sub(r"[^a-z0-9]+", "-", self.label.lower()).strip("-")[:32]
        digest = hashlib.sha1(self.ref.encode()).hexdigest()[:8]
        return f"{stem}-{digest}"

    @property
    def ok(self) -> bool:
        return not self.error and not self.blocking and self.total > 0 and self.passed == self.total


def run(argv: list[str], timeout: int) -> tuple[int, str]:
    """Run a command and hand back its exit code and combined output.

    gecko inspect exits non-zero when it finds a blocking issue, so a non-zero code
    here is a result to read, not a crash to raise on.
    """
    try:
        done = subprocess.run(
            argv, capture_output=True, text=True, timeout=timeout, env={**os.environ, "GECKO_TELEMETRY": "off"}
        )
    except subprocess.TimeoutExpired:
        return 124, f"timed out after {timeout}s"
    except FileNotFoundError:
        return 127, f"command not found: {argv[0]}"
    return done.returncode, done.stdout + done.stderr


def survey_one(ref: str, out_dir: Path) -> Lane:
    """One lane. Grades the spec, then proves its calls offline."""
    lane = Lane(ref=ref)
    report = out_dir / f"{lane.slug}.inspect.json"
    # A report left behind by an earlier run would be read as this run's result.
    report.unlink(missing_ok=True)

    code, text = run([*GECKO, "inspect", ref, "-o", str(report)], LANE_TIMEOUT)
    if not report.exists():
        last = text.strip().splitlines()[-1:] or ["no output"]
        lane.error = f"inspect produced no report (exit {code}): {last[0]}"
        return lane
    data = json.loads(report.read_text())
    lane.grade = data["grade"]
    lane.score = data["score"]
    lane.blocking = [
        f"{f['location']}: {f['message']}"
        for dim in data["dimensions"]
        for f in dim["findings"]
        if f["severity"] == "blocking"
    ]

    code, text = run([*GECKO, "test", ref], LANE_TIMEOUT)
    (out_dir / f"{lane.slug}.test.txt").write_text(text)
    lane.passed = text.count("[PASS]")
    lane.total = lane.passed + text.count("[FAIL]")
    if lane.total == 0:
        lane.error = lane.error or f"test produced no checks (exit {code})"
    return lane


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("refs", nargs="*", default=[str(p) for p in DEFAULT_SPECS],
                    help="spec paths or URLs (default: everything in workflows/specs/)")
    ap.add_argument("--out", default=str(HERE / "out"), help="where the artifacts land")
    args = ap.parse_args()

    refs = args.refs or [str(p) for p in DEFAULT_SPECS]
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"fan-out: {len(refs)} candidate(s), all at once\n")
    with ThreadPoolExecutor(max_workers=len(refs)) as pool:
        lanes = list(pool.map(lambda r: survey_one(r, out_dir), refs))

    print("verify:\n")
    print(f"  {'candidate':<34} {'grade':<7} {'blocking':<9} {'calls':<8} verdict")
    for lane in sorted(lanes, key=lambda x: (not x.ok, x.ref)):
        calls = f"{lane.passed}/{lane.total}" if lane.total else "-"
        verdict = "ready" if lane.ok else "not ready"
        print(f"  {lane.label[:34]:<34} {lane.grade + ' ' + str(lane.score):<7} "
              f"{len(lane.blocking):<9} {calls:<8} {verdict}")

    failed = [lane for lane in lanes if not lane.ok]
    for lane in failed:
        print(f"\n  {lane.label} is not ready:")
        if lane.error:
            print(f"    - {lane.error}")
        for item in lane.blocking:
            print(f"    - blocking: {item}")
        if lane.total and lane.passed != lane.total:
            print(f"    - {lane.total - lane.passed} offline call check(s) failed")

    print(f"\n  artifacts in {out_dir}")
    if failed:
        print(f"  {len(failed)} of {len(lanes)} candidate(s) refused")
        return 1
    print(f"  {len(lanes)} of {len(lanes)} candidate(s) ready")
    return 0


if __name__ == "__main__":
    sys.exit(main())
