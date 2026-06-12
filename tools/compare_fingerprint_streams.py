"""Compare two benchmark fingerprint JSONL artifacts."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.replay.fingerprint_stream import compare_fingerprint_streams


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("left")
    parser.add_argument("right")
    args = parser.parse_args()

    comparison = compare_fingerprint_streams(args.left, args.right)
    print(json.dumps(comparison, indent=2))
    if comparison["rounded"] is not None:
        sys.exit(1)


if __name__ == "__main__":
    main()
