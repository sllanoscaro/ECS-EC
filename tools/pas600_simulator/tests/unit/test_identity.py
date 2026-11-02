"""Domain-separated canonical identity must ignore mapping insertion order."""
from pas600_simulator.identity import digest


def test_canonical_identity():
    """Equal objects hash equally while separate semantic domains cannot alias."""
    assert digest('logical-v1', {'a': 1, 'b': 2}) == digest('logical-v1', {'b': 2, 'a': 1})
    assert digest('logical-v1', {'a': 1}) != digest('complete-v1', {'a': 1})


def test_scenario_format_and_order():
    """Wire format changes full identity only; category order cannot change samples."""
    from pas600_simulator.scenario import SimulationScenario
    from pas600_simulator.identity import scenario_hashes
    scenario = SimulationScenario()
    original = scenario_hashes(scenario)
    scenario.categories.reverse()
    assert scenario_hashes(scenario) == original
    scenario.format = 'json'
    changed = scenario_hashes(scenario)
    assert changed[0] == original[0]
    assert changed[1] != original[1]
