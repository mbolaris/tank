"""Tests for the deterministic ranked-choice tally (``tools/tally_proposals.py``).

These exercise the pure parsing + instant-runoff logic; no network is involved.
"""

import sys
from pathlib import Path

# tools/ is not a package; put it on the path like the tool does for its sibling import.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

import tally_proposals as tp


def _c(cid, tags, author="m", text="", metrics=None):
    return {"id": cid, "author": author, "tags": tags, "text": text, "metrics": metrics or {}}


# --- parsing -----------------------------------------------------------------


def test_extract_proposals_uses_comment_id_and_title():
    comments = [
        _c(48, ["proposal"], author="GPT-5", text="TITLE: Coevolve the tank | vision: …"),
        _c(49, ["proposal"], author="Claude", text="no title here, just prose"),
        _c(50, ["observation"], text="not a proposal"),
    ]
    props = tp.extract_proposals(comments)
    assert set(props) == {48, 49}
    assert props[48]["title"] == "Coevolve the tank"
    assert props[48]["author"] == "GPT-5"
    assert props[49]["title"] == "no title here, just prose"


def test_ranking_filters_invalid_orders_by_suffix_and_dedups():
    valid = {1, 2}
    # out-of-order keys, an invalid id (99), a duplicate, and keep-looking (0)
    metrics = {"rank2": 0, "rank1": 2, "rank3": 99, "rank4": 2}
    assert tp._ranking_from_metrics(metrics, valid) == [2, 0]


def test_extract_ballots_takes_latest_per_author():
    comments = [
        _c(10, ["vote"], author="GPT-5", metrics={"rank1": 1}),
        _c(20, ["vote"], author="GPT-5", metrics={"rank1": 2}),  # supersedes #10
        _c(11, ["vote"], author="Claude", metrics={"rank1": 1, "rank2": 0}),
    ]
    ballots = tp.extract_ballots(comments, valid_ids={1, 2})
    assert ballots == {"GPT-5": [2], "Claude": [1, 0]}


# --- instant-runoff ----------------------------------------------------------


def test_irv_first_round_majority():
    res = tp.instant_runoff([[1], [1], [2]])
    assert res["winner"] == 1 and res["majority"] is True
    assert len(res["rounds"]) == 1


def test_irv_runoff_transfers_to_winner():
    # 1:2, 2:2, 3:1 → eliminate 3 → its [3,1] ballot flows to 1 → 1 wins 3–2
    ballots = [[1, 3], [1, 3], [2, 3], [2, 3], [3, 1]]
    res = tp.instant_runoff(ballots)
    assert res["winner"] == 1
    assert res["rounds"][0]["eliminated"] == 3


def test_irv_keep_looking_can_win():
    res = tp.instant_runoff([[0], [0], [1]])
    assert res["winner"] == tp.KEEP_LOOKING


def test_irv_elimination_and_leader_tiebreaks_are_deterministic():
    # 1 and 2 tie; lower id leads, higher id is eliminated first → 1 wins.
    res = tp.instant_runoff([[2], [1]])
    assert res["winner"] == 1
    assert res["rounds"][0]["eliminated"] == 2


def test_irv_no_ballots():
    assert tp.instant_runoff([])["winner"] is None


# --- end-to-end tally + quorum ----------------------------------------------


def test_tally_marks_provisional_below_quorum():
    comments = [
        _c(1, ["proposal"], author="GPT-5", text="TITLE: A"),
        _c(2, ["proposal"], author="Claude", text="TITLE: B"),
        _c(3, ["vote"], author="GPT-5", metrics={"rank1": 1}),
        _c(4, ["vote"], author="Claude", metrics={"rank1": 1, "rank2": 2}),
    ]
    t = tp.tally(comments)
    assert t["winner"] == 1
    assert t["voters"] == 2
    assert t["provisional"] is True  # binding winner but < 3 voters
    assert "#1" in tp.format_result(t)


def test_tally_binding_with_quorum():
    comments = [
        _c(1, ["proposal"], author="GPT-5", text="TITLE: A"),
        _c(2, ["proposal"], author="Claude", text="TITLE: B"),
        _c(3, ["vote"], author="GPT-5", metrics={"rank1": 1}),
        _c(4, ["vote"], author="Claude", metrics={"rank1": 1}),
        _c(5, ["vote"], author="Gemini", metrics={"rank1": 2, "rank2": 1}),
    ]
    t = tp.tally(comments)
    assert t["winner"] == 1
    assert t["voters"] == 3
    assert t["provisional"] is False
