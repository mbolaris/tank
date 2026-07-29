"""Bit-exact fingerprint of the float primitives the simulation depends on.

Why this exists
---------------
Tank benchmarks reproduce bit-for-bit within a machine but not across them:
``tank/ecosystem_health_10k`` seed 42 scores 10.150218544250826 on a
Windows/CPython 3.14 dev box and 9.967411959401476 on CI's Linux/CPython 3.10,
for the same commit, with matching ``config_hash`` and with ``PYTHONHASHSEED``
ruled out. That forces champions to be re-baselined from CI artifacts rather
than locally, and it means a "regression" can be nothing but a change of
machine.

IEEE 754 pins ``+ - * /`` and ``sqrt`` to correctly-rounded results, but says
nothing about transcendentals: ``sin``, ``exp``, ``pow`` and friends come from
the platform libm and are free to differ in the last ulp between Windows,
glibc and macOS. Over a chaotic 10k-frame simulation, one ulp is enough to
change which fish reaches which food first, and from there everything.

This prints a hash per primitive so two environments can be diffed directly,
turning "the numbers differ somehow" into "``sin`` differs, ``sqrt`` does not".

Usage
-----
    python tools/float_fingerprint.py

Run it on both machines and diff. Identical lines exonerate that primitive;
differing lines are a concrete mechanism. Note this checks the *primitives*,
not the simulation - matching output here does not prove a benchmark agrees,
only that this particular explanation is not the cause.
"""

from __future__ import annotations

import hashlib
import math
import platform
import random
import struct
import sys
from collections.abc import Callable, Iterable


def _bits(value: float) -> str:
    """Exact bit pattern, so near-equal values still compare unequal."""
    return struct.pack(">d", float(value)).hex()


def _digest(values: Iterable[float]) -> str:
    accumulator = hashlib.sha256()
    for value in values:
        accumulator.update(_bits(value).encode())
    return accumulator.hexdigest()[:32]


UNARY_INPUTS = [0.1, 0.5, 1.0, 1.5, 2.0, 3.7, 10.0, 123.456, 1e-8, 1e8, 0.30000000000000004]
BINARY_INPUTS = [(3.0, 4.0), (1e-8, 1.0), (0.1, 0.2), (123.456, 78.9), (1.0, 1e8), (-3.3, 7.7)]


def _unary() -> dict[str, Callable[[float], float]]:
    return {
        # Correctly rounded per IEEE 754 - these should never differ, and are
        # included precisely so a difference here means something much worse
        # than a libm mismatch.
        "sqrt": math.sqrt,
        # Platform libm, free to differ in the last ulp.
        "sin": math.sin,
        "cos": math.cos,
        "tan": math.tan,
        "atan": math.atan,
        "exp": lambda v: math.exp(min(v, 700.0)),
        "log": lambda v: math.log(abs(v)) if v else 0.0,
        "asin": lambda v: math.asin(max(-1.0, min(1.0, v))),
    }


def report() -> list[str]:
    lines = [
        f"# python {sys.version.split()[0]} on {sys.platform} "
        f"({platform.machine()}, {platform.system()})",
    ]

    for name, function in _unary().items():
        lines.append(f"{name:8} {_digest(function(v) for v in UNARY_INPUTS)}")

    # Movement code leans on these hardest, and CPython's hypot implementation
    # has been revised more than once, so a version bump alone can move it.
    lines.append(f"{'hypot':8} {_digest(math.hypot(a, b) for a, b in BINARY_INPUTS)}")
    lines.append(f"{'atan2':8} {_digest(math.atan2(a, b) for a, b in BINARY_INPUTS)}")
    # abs() on the base: a negative base with a fractional exponent returns
    # a complex number rather than a float.
    lines.append(f"{'pow':8} {_digest(abs(a) ** b for a, b in BINARY_INPUTS)}")
    lines.append(f"{'mathpow':8} {_digest(math.pow(abs(a), b) for a, b in BINARY_INPUTS)}")

    # Mersenne Twister is specified exactly, so these should be identical
    # everywhere; if they are not, the problem is far more fundamental than
    # libm rounding.
    rng = random.Random(42)
    lines.append(f"{'random':8} {_digest(rng.random() for _ in range(500))}")
    rng = random.Random(42)
    lines.append(f"{'gauss':8} {_digest(rng.gauss(0.0, 1.0) for _ in range(500))}")
    rng = random.Random(42)
    lines.append(f"{'uniform':8} {_digest(rng.uniform(-10.0, 10.0) for _ in range(500))}")
    rng = random.Random(42)
    integers = hashlib.sha256()
    for _ in range(500):
        integers.update(str(rng.randint(0, 1_000_000)).encode())
    lines.append(f"{'randint':8} {integers.hexdigest()[:32]}")

    # Summation order effects, which differ if anything vectorises.
    sequence = [0.1] * 100 + [1e16, -1e16]
    lines.append(f"{'sum':8} {_bits(sum(sequence))}")
    lines.append(f"{'fsum':8} {_bits(math.fsum(sequence))}")

    return lines


def main() -> None:
    print("\n".join(report()))


if __name__ == "__main__":
    main()
