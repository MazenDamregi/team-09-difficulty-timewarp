"""
I2 — Shock tests.

Sides: A3 (scenarios) + B2 (ASERT).
Leader: Mazen Damergi.

Done when:
  Metrics table complete; every rule recovers from the −50 % drop.
"""

from difficulty_timewarp.sim import Simulator, Scenario
from difficulty_timewarp.rules import bitcoin_window, asert, moving_average
from difficulty_timewarp.eval import metrics_table, recovery_blocks


def test_all_rules_all_scenarios():
    """All 3 rules × 4 scenarios produce valid metrics."""
    window = 100
    sim = Simulator(target_interval=600.0)
    rules = {
        "bitcoin_window": lambda b, ti: bitcoin_window(b, ti, window=window),
        "asert": lambda b, ti: asert(b, ti, half_life=60000.0),
        "moving_avg": lambda b, ti: moving_average(b, ti, k=50),
    }
    scenarios = Scenario.all_scenarios()

    results = {}
    for rname, rule in rules.items():
        results[rname] = {}
        for scen in scenarios:
            blocks = sim.simulate(rule, scen, 15000, seed=42)
            results[rname][scen.name] = blocks

    table = metrics_table(results, shock_block=5000)

    # Every cell should be filled.
    for rname in rules:
        for scen in scenarios:
            m = table[rname][scen.name]
            assert m["mean_time"] > 0
            assert m["oscillation"] >= 1.0


def test_every_rule_recovers_from_drop():
    """Every rule eventually recovers from the −50 % hash-rate drop."""
    window = 100
    sim = Simulator(target_interval=600.0)
    rules = {
        "bitcoin_window": lambda b, ti: bitcoin_window(b, ti, window=window),
        "asert": lambda b, ti: asert(b, ti, half_life=60000.0),
        "moving_avg": lambda b, ti: moving_average(b, ti, k=50),
    }

    for rname, rule in rules.items():
        blocks = sim.simulate(
            rule, Scenario.drop_50(at_block=5000), 20000, seed=42
        )
        # After the drop, equilibrium difficulty should be ~0.5.
        # Check recovery to within 20 % of 0.5.
        rec = recovery_blocks(blocks, target_difficulty=0.5, threshold=0.20, shock_block=5000)
        assert rec != -1, f"{rname} never recovered from the 50 % drop"
