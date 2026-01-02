from core.genetics.trait import GeneticTrait, apply_trait_meta_to_trait, trait_meta_for_trait


def test_trait_meta_for_trait_omits_defaults() -> None:
    trait = GeneticTrait(1.0)
    assert trait_meta_for_trait(trait) == {}


def test_apply_trait_meta_to_trait_clamps_and_round_trips() -> None:
    trait = GeneticTrait(1.0)

    apply_trait_meta_to_trait(
        trait,
        {
            "mutation_rate": -1.0,
            "mutation_strength": 0.75,
            "hgt_probability": 2.0,
        },
    )

    assert trait.mutation_rate == 0.0
    assert trait.mutation_strength == 0.75
    assert trait.hgt_probability == 1.0

    assert trait_meta_for_trait(trait) == {
        "mutation_rate": 0.0,
        "mutation_strength": 0.75,
        "hgt_probability": 1.0,
    }
