"""Test script to verify algorithm performance tracking system."""

from core.algorithms import ALL_ALGORITHMS
from core.ecosystem import EcosystemManager


def test_algorithm_stats():
    """Test the algorithm statistics tracking."""
    print("Testing Algorithm Performance Tracking System")
    print("=" * 80)

    # Create ecosystem manager
    ecosystem = EcosystemManager(max_population=50)

    # Verify algorithm stats are initialized
    print("\n1. Testing initialization...")
    print(f"   Total algorithms initialized: {len(ecosystem.algorithm_stats)}")
    assert len(ecosystem.algorithm_stats) == 53, "Should have 53 algorithms"
    print("   ✓ All 53 algorithms initialized")

    # Test a few algorithm names
    print("\n2. Testing algorithm names...")
    for i in range(min(5, len(ALL_ALGORITHMS))):
        algo_class = ALL_ALGORITHMS[i]
        stats = ecosystem.algorithm_stats[i]
        print(f"   Algorithm {i}: {stats.algorithm_name}")
        assert stats.algorithm_name == algo_class.__name__
    print("   ✓ Algorithm names match")

    # Test recording births
    print("\n3. Testing birth recording...")
    ecosystem.record_birth(fish_id=1, generation=0, algorithm_id=0)
    ecosystem.record_birth(fish_id=2, generation=0, algorithm_id=0)
    ecosystem.record_birth(fish_id=3, generation=0, algorithm_id=5)
    assert ecosystem.algorithm_stats[0].total_births == 2
    assert ecosystem.algorithm_stats[0].current_population == 2
    assert ecosystem.algorithm_stats[5].total_births == 1
    print("   ✓ Births recorded correctly")

    # Test recording deaths
    print("\n4. Testing death recording...")
    ecosystem.record_death(fish_id=1, generation=0, age=100, cause="starvation", algorithm_id=0)
    assert ecosystem.algorithm_stats[0].total_deaths == 1
    assert ecosystem.algorithm_stats[0].deaths_starvation == 1
    assert ecosystem.algorithm_stats[0].current_population == 1
    assert ecosystem.algorithm_stats[0].total_lifespan == 100
    print("   ✓ Deaths recorded correctly")

    # Test recording reproduction
    print("\n5. Testing reproduction recording...")
    ecosystem.record_reproduction(algorithm_id=0)
    ecosystem.record_reproduction(algorithm_id=0)
    assert ecosystem.algorithm_stats[0].total_reproductions == 2
    print("   ✓ Reproductions recorded correctly")

    # Test recording food consumption
    print("\n6. Testing food consumption recording...")
    ecosystem.record_food_eaten(algorithm_id=0)
    ecosystem.record_food_eaten(algorithm_id=0)
    ecosystem.record_food_eaten(algorithm_id=0)
    assert ecosystem.algorithm_stats[0].total_food_eaten == 3
    print("   ✓ Food consumption recorded correctly")

    # Test performance metrics
    print("\n7. Testing performance metrics...")
    stats = ecosystem.algorithm_stats[0]
    avg_lifespan = stats.get_avg_lifespan()
    reproduction_rate = stats.get_reproduction_rate()
    survival_rate = stats.get_survival_rate()
    print(f"   Avg Lifespan: {avg_lifespan}")
    print(f"   Reproduction Rate: {reproduction_rate:.2%}")
    print(f"   Survival Rate: {survival_rate:.2%}")
    assert avg_lifespan == 100.0
    assert reproduction_rate == 1.0  # 2 reproductions / 2 births
    assert survival_rate == 0.5  # 1 alive / 2 births
    print("   ✓ Performance metrics calculated correctly")

    # Test report generation
    print("\n8. Testing report generation...")
    # Add more data for a better report
    for i in range(10):
        ecosystem.record_birth(fish_id=100 + i, generation=1, algorithm_id=1)
        ecosystem.record_food_eaten(algorithm_id=1)
    for i in range(7):
        ecosystem.record_death(
            fish_id=100 + i, generation=1, age=150, cause="old_age", algorithm_id=1
        )
    ecosystem.record_reproduction(algorithm_id=1)
    ecosystem.record_reproduction(algorithm_id=1)
    ecosystem.record_reproduction(algorithm_id=1)

    report = ecosystem.get_algorithm_performance_report(min_sample_size=2)
    assert len(report) > 0
    assert "ALGORITHM PERFORMANCE REPORT" in report
    assert "TOP PERFORMING ALGORITHMS" in report
    print("   ✓ Report generated successfully")
    print("\n   Report preview (first 500 chars):")
    print("   " + "-" * 76)
    for line in report[:500].split("\n"):
        print(f"   {line}")
    print("   " + "-" * 76)

    print("\n" + "=" * 80)
    print("ALL TESTS PASSED! ✓")
    print("=" * 80)

    # Print full report
    print("\n\nFULL ALGORITHM PERFORMANCE REPORT:")
    print(report)


if __name__ == "__main__":
    test_algorithm_stats()
