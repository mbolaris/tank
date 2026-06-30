from tools.composable_cfr_inheritance_assay import run_assay


def test_composable_cfr_inheritance_assay_observes_activation():
    result = run_assay(seed=42)

    assert result["passed"] is True
    assert result["parent_info_sets"] == 3
    assert result["inherited_info_sets"] == result["parent_info_sets"]
    assert result["reset_info_sets"] == 0
    assert result["inherited_total_visits_before_activation"] == 0
    assert all(case["decay_ok"] for case in result["cases"])
    assert any(case["inherited_overrode_reset"] for case in result["cases"])
