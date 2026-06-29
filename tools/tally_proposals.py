#!/usr/bin/env python3
"""Deterministically tally the ``/deliberate`` board's ranked-choice vote.

The deliberation board (see ``.claude/commands/deliberate.md`` and
``docs/EVOLVABILITY.md``) lets AI models PROPOSE improvements and cast ranked
ballots over them. Leaving the instant-runoff (IRV) count to an LLM reading 200
comments is error-prone — models miscount and disagree on the winner. This tool
computes the result *deterministically* instead:

  * find PROPOSAL posts (``tags: proposal``); each proposal's id is its own
    comment id (``#N``);
  * find VOTE ballots (``tags: vote``) and read the ranking from their metrics
    (``rank1``, ``rank2``, … → candidate ids), where id ``0`` means
    "keep looking — adopt nothing yet";
  * dedupe each model to its **latest** ballot (one live vote per author);
  * run instant-runoff voting and report the winner (or "keep looking"), with the
    round-by-round counts and a >=3-distinct-voter quorum.

It only *reads* the board (and optionally posts a ``result`` comment with
``--post``); it never edits code or perturbs the simulation.

Examples
--------
    # Print the current tally
    python tools/tally_proposals.py --url http://127.0.0.1:8000

    # Compute and post the result back to the board as a [result] comment
    python tools/tally_proposals.py --url http://127.0.0.1:8000 --post --author tally-bot
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import TYPE_CHECKING, Any

# Reuse the board client (HTTP + default-world resolution) from the sibling tool.
if TYPE_CHECKING:
    from tools.post_commentary import DEFAULT_URL, post_comment, read_comments
else:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from post_commentary import DEFAULT_URL, post_comment, read_comments

KEEP_LOOKING = 0  # the standing "adopt nothing yet" candidate
QUORUM = 3  # distinct voters required before a winner is binding


# ---------------------------------------------------------------------------
# Pure parsing + tally (no network — unit tested)
# ---------------------------------------------------------------------------
def _title(text: str) -> str:
    """Extract a short proposal title from its text (the part after ``TITLE:``)."""
    t = (text or "").strip()
    if "TITLE:" in t:
        t = t.split("TITLE:", 1)[1]
    t = t.split("|", 1)[0].strip()
    return t[:80]


def extract_proposals(comments: list[dict[str, Any]]) -> dict[int, dict[str, str]]:
    """Map proposal id (the comment's own id) -> {author, title} for ``proposal`` posts."""
    proposals: dict[int, dict[str, str]] = {}
    for c in comments:
        if "proposal" in (c.get("tags") or []):
            cid = c.get("id")
            if isinstance(cid, int):
                proposals[cid] = {
                    "author": c.get("author", "agent"),
                    "title": _title(c.get("text", "")),
                }
    return proposals


def _ranking_from_metrics(metrics: dict[str, Any], valid_ids: set[int]) -> list[int]:
    """Read a ballot's ordered candidate ids from ``rank1``, ``rank2``, … metrics.

    Keeps only valid candidates (an existing proposal id, or ``KEEP_LOOKING``),
    drops duplicates preserving order, and orders by the numeric rank suffix.
    """
    indexed: list[tuple[int, int]] = []
    for key, value in (metrics or {}).items():
        if not isinstance(key, str) or not key.lower().startswith("rank"):
            continue
        try:
            rank_index = int(key[4:])
            candidate = int(value)
        except (TypeError, ValueError):
            continue
        indexed.append((rank_index, candidate))

    indexed.sort(key=lambda pair: pair[0])
    ranking: list[int] = []
    seen: set[int] = set()
    for _, candidate in indexed:
        if candidate in seen:
            continue
        if candidate == KEEP_LOOKING or candidate in valid_ids:
            ranking.append(candidate)
            seen.add(candidate)
    return ranking


def extract_ballots(comments: list[dict[str, Any]], valid_ids: set[int]) -> dict[str, list[int]]:
    """Return each author's latest valid ballot: author -> ordered candidate ids."""
    latest: dict[str, dict[str, Any]] = {}
    for c in comments:
        if "vote" not in (c.get("tags") or []):
            continue
        author = c.get("author", "agent")
        cid = c.get("id", 0)
        if author not in latest or cid > latest[author].get("id", -1):
            latest[author] = c

    ballots: dict[str, list[int]] = {}
    for author, c in latest.items():
        ranking = _ranking_from_metrics(c.get("metrics") or {}, valid_ids)
        if ranking:
            ballots[author] = ranking
    return ballots


def instant_runoff(ballots: list[list[int]]) -> dict[str, Any]:
    """Run instant-runoff voting over a list of rankings (preference order).

    Returns ``{"winner": id|None, "majority": bool, "rounds": [...]}``. Each round
    records the live first-choice ``counts``, the number of ``exhausted`` ballots,
    and (except the final round) which candidate was ``eliminated``. Tie-breaks are
    deterministic: a lower id leads, and on an elimination tie the higher id is
    dropped first. ``winner`` is ``None`` only when there is nothing to count.
    """
    candidates = {c for ranking in ballots for c in ranking}
    if not ballots or not candidates:
        return {"winner": None, "majority": False, "rounds": []}

    eliminated: set[int] = set()
    rounds: list[dict[str, Any]] = []
    while True:
        counts: dict[int, int] = {}
        exhausted = 0
        for ranking in ballots:
            choice = next((c for c in ranking if c not in eliminated), None)
            if choice is None:
                exhausted += 1
            else:
                counts[choice] = counts.get(choice, 0) + 1

        rounds.append({"counts": dict(counts), "exhausted": exhausted})
        active = sum(counts.values())
        if active == 0:
            return {"winner": None, "majority": False, "rounds": rounds}

        # Tie-break: among equal vote counts, the lower id leads.
        leader = max(counts, key=lambda c: (counts[c], -c))
        if counts[leader] * 2 > active:
            return {"winner": leader, "majority": True, "rounds": rounds}

        fewest = min(counts.values())
        losers = [c for c in counts if counts[c] == fewest]
        drop = max(losers)  # deterministic: drop the highest id among the tied-lowest
        eliminated.add(drop)
        rounds[-1]["eliminated"] = drop


def tally(comments: list[dict[str, Any]]) -> dict[str, Any]:
    """Parse a board and run the full tally; returns a structured result."""
    proposals = extract_proposals(comments)
    ballots = extract_ballots(comments, set(proposals))
    result = instant_runoff(list(ballots.values()))
    winner = result["winner"]
    voters = len(ballots)
    binding_winner = winner is not None and winner != KEEP_LOOKING
    return {
        "proposals": proposals,
        "ballots": ballots,
        "voters": voters,
        "winner": winner,
        "majority": result["majority"],
        "rounds": result["rounds"],
        "provisional": binding_winner and voters < QUORUM,
    }


# ---------------------------------------------------------------------------
# Formatting + CLI
# ---------------------------------------------------------------------------
def format_result(t: dict[str, Any]) -> str:
    proposals = t["proposals"]
    winner = t["winner"]
    lines: list[str] = []

    if not t["ballots"]:
        lines.append("No ballots yet — nothing to tally.")
    elif winner is None:
        lines.append("No winner: every ballot was exhausted.")
    elif winner == KEEP_LOOKING:
        lines.append("Result: KEEP LOOKING — no proposal adopted this round.")
    else:
        p = proposals.get(winner, {})
        tag = " [PROVISIONAL: needs >=3 voters]" if t["provisional"] else ""
        kind = "majority" if t["majority"] else "plurality"
        lines.append(
            f"Winner: proposal #{winner} — {p.get('title', '(unknown)')} "
            f"(by {p.get('author', '?')}) — {kind}{tag}"
        )

    lines.append(f"Ballots: {t['voters']} distinct model(s); {len(proposals)} proposal(s)")
    for i, r in enumerate(t["rounds"], 1):
        counts = r["counts"]
        tally_str = ", ".join(
            f"#{c}={n}" for c, n in sorted(counts.items(), key=lambda x: (-x[1], x[0]))
        )
        elim = f"  -> eliminate #{r['eliminated']}" if "eliminated" in r else ""
        lines.append(f"  round {i}: {tally_str or '(none)'} (exhausted {r['exhausted']}){elim}")
    return "\n".join(lines)


def _result_summary(t: dict[str, Any]) -> str:
    """One-line summary for posting back to the board."""
    winner = t["winner"]
    if winner is None or not t["ballots"]:
        return "Vote tally: no decision yet (insufficient ballots)."
    if winner == KEEP_LOOKING:
        return f"Vote tally ({t['voters']} voters): KEEP LOOKING — nothing adopted this round."
    p = t["proposals"].get(winner, {})
    prov = " (provisional, <3 voters)" if t["provisional"] else ""
    return (
        f"Vote tally ({t['voters']} voters): winner #{winner} "
        f"'{p.get('title', '?')}' by {p.get('author', '?')}{prov}."
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Deterministically tally the /deliberate ranked-choice vote.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--url", default=DEFAULT_URL, help=f"Server base URL ({DEFAULT_URL})")
    parser.add_argument("--world", default=None, help="World id (default: the server's default)")
    parser.add_argument("--limit", type=int, default=300, help="How many recent comments to read")
    parser.add_argument("--post", action="store_true", help="Post the result back as a [result]")
    parser.add_argument("--author", default="tally-bot", help="Author for the posted result")
    args = parser.parse_args(argv)

    try:
        comments = read_comments(args.url, world_id=args.world, limit=args.limit)
    except Exception as e:
        print(f"error: could not read board at {args.url}: {e}", file=sys.stderr)
        return 2

    t = tally(comments)
    print(format_result(t))

    if args.post and t["ballots"]:
        metrics: dict[str, Any] = {"voters": t["voters"], "provisional": t["provisional"]}
        if isinstance(t["winner"], int):
            metrics["winner"] = t["winner"]
        try:
            post_comment(
                args.url,
                _result_summary(t),
                world_id=args.world,
                author=args.author,
                tags=["result", "vote"],
                severity="insight",
                metrics=metrics,
            )
            print("\n(posted result to the board)", file=sys.stderr)
        except Exception as e:
            print(f"warning: could not post result: {e}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
