from synthetix.blueprints.models import PopulationSpec
from synthetix.population.sampler import sample_population


def test_population_sampling_is_seeded_and_balanced() -> None:
    spec = PopulationSpec(
        size=6,
        seed=23,
        attributes={"region": ["north", "south"], "attitude": ["skeptical", "curious"]},
    )
    first = sample_population(spec)
    second = sample_population(spec)
    assert first == second
    assert len(first) == 6
    assert {persona.attributes["region"] for persona in first} == {"north", "south"}
    assert len({persona.id for persona in first}) == 6

