"""Run multiple poker simulations and print summary statistics."""
import sys
import statistics
sys.path.append(r"c:\shared\bolaris\tank")
from core.poker.core import simulate_game, finalize_pot


def run(n=100):
    winners = {1: 0, 2: 0, 'split': 0}
    pots = []
    folds = 0

    for _ in range(n):
        s = simulate_game(bet_amount=10.0, player1_energy=100.0, player2_energy=100.0)
        if s.player1_folded and not s.player2_folded:
            winners[2] += 1
            folds += 1
        elif s.player2_folded and not s.player1_folded:
            winners[1] += 1
            folds += 1
        else:
            p1_amount, p2_amount = finalize_pot(s)
            if p1_amount > p2_amount:
                winners[1] += 1
            elif p2_amount > p1_amount:
                winners[2] += 1
            else:
                winners['split'] += 1
        pots.append(s.pot)

    print(f"Ran {n} simulations")
    print("Winners:", winners)
    print("Average pot:", statistics.mean(pots) if pots else 0)
    print("Median pot:", statistics.median(pots) if pots else 0)
    print("Fold rate:", folds / n)


if __name__ == '__main__':
    run(100)
