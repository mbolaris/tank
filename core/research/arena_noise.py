"""Pure statistics for the Champions Tank noise study (A0).

The question A0 answers is whether a house's population share in an arena
match is set by *which house it is* or by *which seed the match ran on*. If
the seed dominates, no admission rule built on shares can tell a better
species from a luckier one, and the arena design has to change before any of
it is built (see docs/CHAMPIONS_TANK.md, section 13).

Everything here is a pure function of a ``shares`` matrix laid out as
``shares[house][seed]`` so the analysis is cheap to test without running a
world. The simulation driver lives in ``tools/arena_noise_study.py``.
"""

from __future__ import annotations

import math
import random
from collections.abc import Callable, Sequence

Matrix = Sequence[Sequence[float]]


def select_seed_pack(
    member_ids: Sequence[int],
    distance: Callable[[int, int], float],
    size: int = 5,
) -> list[int]:
    """Pick a taxon's medoid plus its most spread-out members.

    The medoid is the member with the smallest summed distance to the rest.
    The remaining picks use farthest-point sampling, so the pack keeps the
    taxon's variation without keeping near-duplicates. Ties break on the
    smaller id, which keeps the selection deterministic.
    """
    ids = sorted(member_ids)
    if len(ids) <= size:
        return ids

    medoid = min(ids, key=lambda a: (sum(distance(a, b) for b in ids), a))
    pack = [medoid]
    nearest = {i: distance(i, medoid) for i in ids if i != medoid}
    while len(pack) < size:
        pick = max(nearest, key=lambda i: (nearest[i], -i))
        pack.append(pick)
        del nearest[pick]
        for i in nearest:
            nearest[i] = min(nearest[i], distance(i, pick))
    return pack


def _house_means(shares: Matrix) -> list[float]:
    return [sum(row) / len(row) for row in shares]


def variance_decomposition(shares: Matrix) -> dict[str, float]:
    """One-way random-effects decomposition of share variance by house.

    Returns the between- and within-house mean squares, the F ratio, eta
    squared (share of total sum of squares explained by house) and ICC(1),
    the fraction of variance attributable to house identity in a single match.
    """
    houses = len(shares)
    seeds = len(shares[0])
    grand = sum(sum(row) for row in shares) / (houses * seeds)
    means = _house_means(shares)

    ss_between = seeds * sum((m - grand) ** 2 for m in means)
    ss_within = sum((v - m) ** 2 for row, m in zip(shares, means, strict=True) for v in row)
    df_between = houses - 1
    df_within = houses * (seeds - 1)
    ms_between = ss_between / df_between
    ms_within = ss_within / df_within if df_within else 0.0

    f_ratio = ms_between / ms_within if ms_within > 0 else math.inf
    icc_denominator = ms_between + (seeds - 1) * ms_within
    icc = (ms_between - ms_within) / icc_denominator if icc_denominator > 0 else 0.0
    total = ss_between + ss_within
    return {
        "houses": float(houses),
        "seeds": float(seeds),
        "ms_between": ms_between,
        "ms_within": ms_within,
        "f_ratio": f_ratio,
        "eta_squared": ss_between / total if total > 0 else 0.0,
        "icc1": icc,
    }


def permutation_p_value(shares: Matrix, permutations: int, rng: random.Random) -> float:
    """P-value for "house identity does not matter".

    Under that null, house labels are exchangeable within each seed, so the
    test shuffles labels inside every seed column and asks how often the
    spread of house means is at least as large as observed. Shuffling within
    seeds respects that shares in one match are not independent (they sum to
    at most one).
    """
    houses = len(shares)
    seeds = len(shares[0])

    def spread(matrix: Matrix) -> float:
        means = _house_means(matrix)
        centre = sum(means) / houses
        return sum((m - centre) ** 2 for m in means)

    observed = spread(shares)
    columns = [[shares[h][s] for h in range(houses)] for s in range(seeds)]
    at_least = 0
    for _ in range(permutations):
        for column in columns:
            rng.shuffle(column)
        permuted = [[columns[s][h] for s in range(seeds)] for h in range(houses)]
        if spread(permuted) >= observed - 1e-15:
            at_least += 1
    return (at_least + 1) / (permutations + 1)


def _ranks(values: Sequence[float]) -> list[float]:
    """Average ranks (1 = smallest), ties sharing their mean rank."""
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        mean_rank = (i + j) / 2 + 1
        for k in range(i, j + 1):
            ranks[order[k]] = mean_rank
        i = j + 1
    return ranks


def kendalls_w(shares: Matrix) -> float:
    """Kendall's coefficient of concordance of house rankings across seeds.

    1.0 means every seed ranks the houses identically; 0.0 means the seeds
    agree no more than chance would. Not tie-corrected, so many extinct
    (zero-share) houses in one seed pull it down slightly.
    """
    houses = len(shares)
    seeds = len(shares[0])
    if houses < 2:
        return 0.0
    columns = [_ranks([shares[h][s] for h in range(houses)]) for s in range(seeds)]
    totals = [sum(columns[s][h] for s in range(seeds)) for h in range(houses)]
    mean_total = sum(totals) / houses
    spread = sum((t - mean_total) ** 2 for t in totals)
    return 12 * spread / (seeds**2 * (houses**3 - houses))


def spearman(a: Sequence[float], b: Sequence[float]) -> float:
    """Spearman rank correlation of two equal-length sequences."""
    ra, rb = _ranks(a), _ranks(b)
    n = len(ra)
    ma, mb = sum(ra) / n, sum(rb) / n
    cov = sum((x - ma) * (y - mb) for x, y in zip(ra, rb, strict=True))
    va = sum((x - ma) ** 2 for x in ra)
    vb = sum((y - mb) ** 2 for y in rb)
    return cov / math.sqrt(va * vb) if va > 0 and vb > 0 else 0.0


def split_half_reliability(shares: Matrix) -> float:
    """Rank agreement between house means on the first and second half of seeds."""
    seeds = len(shares[0])
    half = seeds // 2
    first = [sum(row[:half]) / half for row in shares]
    second = [sum(row[half : 2 * half]) / half for row in shares]
    return spearman(first, second)


def paired_difference_sd(shares: Matrix) -> float:
    """Pooled per-seed SD of the share difference between two houses.

    An admission compares a challenger with one incumbent on the same seeds,
    so the noise that matters is the spread of their paired difference, not
    of either share alone. Pooled over every house pair.
    """
    houses = len(shares)
    seeds = len(shares[0])
    pooled = 0.0
    df = 0
    for i in range(houses):
        for j in range(i + 1, houses):
            diffs = [shares[i][s] - shares[j][s] for s in range(seeds)]
            mean = sum(diffs) / seeds
            pooled += sum((d - mean) ** 2 for d in diffs)
            df += seeds - 1
    return math.sqrt(pooled / df) if df else 0.0


def admission_margin(paired_sd: float, seeds: int, z: float = 1.645) -> float:
    """Share margin a challenger must clear so a no-better challenger passes <5% of the time.

    One-sided normal approximation on the mean paired difference over
    ``seeds`` matches.
    """
    return z * paired_sd / math.sqrt(seeds)


def resolvable_pair_fraction(shares: Matrix, seeds: int, z: float = 1.645) -> float:
    """Fraction of house pairs whose observed gap exceeds the admission margin at ``seeds``."""
    means = _house_means(shares)
    margin = admission_margin(paired_difference_sd(shares), seeds, z)
    pairs = [
        abs(means[i] - means[j]) > margin
        for i in range(len(means))
        for j in range(i + 1, len(means))
    ]
    return sum(pairs) / len(pairs) if pairs else 0.0


def sign_test_p(wins: int, losses: int) -> float:
    """Exact two-sided binomial sign test for ``wins`` vs ``losses`` (ties dropped)."""
    n = wins + losses
    if n == 0:
        return 1.0
    k = min(wins, losses)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / float(2**n)
    return float(min(1.0, 2 * tail))


def summarize_pair(
    first_shares: Sequence[float], second_shares: Sequence[float]
) -> dict[str, float]:
    """Head-to-head readout for one pair of houses over matched seeds."""
    diffs = [a - b for a, b in zip(first_shares, second_shares, strict=True)]
    wins = sum(d > 0 for d in diffs)
    losses = sum(d < 0 for d in diffs)
    n = len(diffs)
    mean = sum(diffs) / n
    sd = math.sqrt(sum((d - mean) ** 2 for d in diffs) / (n - 1)) if n > 1 else 0.0
    decided = wins + losses
    return {
        "wins": wins,
        "losses": losses,
        "ties": n - decided,
        "mean_difference": mean,
        "difference_sd": sd,
        "majority_agreement": max(wins, losses) / decided if decided else 0.0,
        "sign_test_p": sign_test_p(wins, losses),
    }


def summarize_shares(
    shares: Matrix,
    alive: Sequence[Sequence[bool]],
    *,
    permutations: int = 2000,
    rng_seed: int = 0,
    admission_seeds: Sequence[int] = (3, 5, 10),
) -> dict[str, object]:
    """Every A0 statistic for one arena configuration, with its verdict."""
    decomposition = variance_decomposition(shares)
    paired_sd = paired_difference_sd(shares)
    p_value = permutation_p_value(shares, permutations, random.Random(rng_seed))
    seeds = len(shares[0])
    return {
        "verdict": verdict(decomposition["icc1"], p_value),
        "variance": decomposition,
        "permutation_p": p_value,
        "kendalls_w": kendalls_w(shares),
        "split_half_spearman": split_half_reliability(shares),
        "paired_difference_sd": paired_sd,
        "admission_margin": {str(n): admission_margin(paired_sd, n) for n in admission_seeds},
        "resolvable_pair_fraction": {
            str(n): resolvable_pair_fraction(shares, n) for n in admission_seeds
        },
        "house_mean_share": _house_means(shares),
        "house_survival_rate": [sum(row) / seeds for row in alive],
    }


def verdict(icc: float, p: float) -> str:
    """Apply the pre-registered A0 decision rule to one configuration.

    Registered in docs/CHAMPIONS_TANK.md before any match ran:
    proceed if house identity explains at least half the single-match
    variance (ICC >= 0.5) and the permutation test rejects exchangeable
    houses (p < 0.01); proceed with more seeds if 0.2 <= ICC < 0.5; redesign
    if ICC < 0.2 or p >= 0.01.
    """
    if p >= 0.01 or icc < 0.2:
        return "redesign"
    if icc < 0.5:
        return "proceed_with_more_seeds"
    return "proceed"
