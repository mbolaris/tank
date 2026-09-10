#!/usr/bin/env python3
"""Report where two benchmark fingerprint streams first diverge.

Answers the five questions a determinism bisect actually starts from - which
frame, which pipeline phase, which entity, which state field, and which RNG
stream - rather than only "the digests differ". See
docs/IMPROVEMENT_PROPOSALS.md 1.0.

Exit status is 1 when the rounded digests diverge, so this doubles as a gate.
Exact-only divergence is reported but does not fail: last-ulp float jitter is
expected across machines, and the rounded stream is the one champions rest on.

Examples::

    python tools/compare_fingerprint_streams.py run1.jsonl run2.jsonl
    python tools/compare_fingerprint_streams.py run1.jsonl run2.jsonl --json
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.replay.fingerprint_diff import compare_fingerprint_streams, format_divergence_report


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("left")
    parser.add_argument("right")
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit the raw comparison instead of the human-readable report.",
    )
    args = parser.parse_args()

    comparison = compare_fingerprint_streams(args.left, args.right)
    if args.json:
        print(json.dumps(comparison, indent=2))
    else:
        print(format_divergence_report(comparison))

    if comparison["rounded"] is not None:
        sys.exit(1)


if __name__ == "__main__":
    main()
