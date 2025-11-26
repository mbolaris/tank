"""
Profile PokerEngine.simulate_multi_round_game to find hotspots.

Usage:
    python scripts/profile_poker_engine.py

This script runs several simulated games under cProfile and prints the top
hotspots by cumulative time. Adjust `N_ITER` for longer/shorter runs.
"""
import cProfile
import pstats
import io
import sys
from time import perf_counter

sys.path.insert(0, r"c:\shared\bolaris\tank")

from core.poker.core import simulate_multi_round_game

N_ITER = 300


def run_once():
    # Use smaller energies and bets to keep each game fast
    simulate_multi_round_game(initial_bet=5.0, player1_energy=100.0, player2_energy=100.0)


def main():
    pr = cProfile.Profile()
    pr.enable()
    t0 = perf_counter()
    for _ in range(N_ITER):
        run_once()
    elapsed = perf_counter() - t0
    pr.disable()

    s = io.StringIO()
    ps = pstats.Stats(pr, stream=s).sort_stats("cumulative")
    ps.print_stats(50)

    print(f"Ran {N_ITER} iterations in {elapsed:.3f}s")
    print(s.getvalue())


if __name__ == "__main__":
    main()
