"""Quick command-line harness for the evolution smoke test."""
from core.evolution.smoke_test import format_report, run_evolution_smoke_test


if __name__ == "__main__":
    report = run_evolution_smoke_test()
    print(format_report(report))
