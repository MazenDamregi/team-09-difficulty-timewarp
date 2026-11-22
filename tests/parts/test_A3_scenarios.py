"""
A3 — Scenarios tests.

Done when:
  - Same seed → identical block series.
  - Four scenarios exported as fixtures.
"""

from difficulty_timewarp.sim import Simulator, Scenario


def _id_rule(blocks, ti):
    return blocks[-1].difficulty


def test_constant_scenario():
    """Constant scenario returns the same hash rate at every height."""
    s = Scenario.constant(2.0)
    for h in [0, 100, 999, 50000]:
        assert s.hashrate_at(h) == 2.0


def test_drop_50_scenario():
    """Hash rate drops by 50 % at the specified block."""
    s = Scenario.drop_50(at_block=100, hashrate=2.0)
    assert s.hashrate_at(99) == 2.0
    assert s.hashrate_at(100) == 1.0
    assert s.hashrate_at(200) == 1.0


def test_jump_3x_scenario():
    """Hash rate triples at the specified block."""
    s = Scenario.jump_3x(at_block=100, hashrate=1.0)
    assert s.hashrate_at(99) == 1.0
    assert s.hashrate_at(100) == 3.0


def test_slow_ramp_scenario():
    """Hash rate ramps linearly."""
    s = Scenario.slow_ramp(start_rate=1.0, end_rate=3.0, over_blocks=1000)
    assert s.hashrate_at(0) == 1.0
    assert abs(s.hashrate_at(500) - 2.0) < 1e-9
    assert s.hashrate_at(1000) == 3.0
    assert s.hashrate_at(2000) == 3.0  # capped


def test_seed_gives_identical_series():
    """Same seed → identical block heights and timestamps."""
    sim = Simulator(target_interval=600.0)
    for scen in Scenario.all_scenarios():
        a = sim.simulate(_id_rule, scen, 200, seed=42)
        b = sim.simulate(_id_rule, scen, 200, seed=42)
        for ba, bb in zip(a, b):
            assert ba.height == bb.height
            assert ba.timestamp == bb.timestamp


def test_different_seed_gives_different_series():
    """Different seeds → different timestamps."""
    sim = Simulator(target_interval=600.0)
    a = sim.simulate(_id_rule, Scenario.constant(), 200, seed=1)
    b = sim.simulate(_id_rule, Scenario.constant(), 200, seed=2)
    # At least one timestamp differs.
    assert any(ba.timestamp != bb.timestamp for ba, bb in zip(a, b))


def test_all_scenarios_returns_four():
    """all_scenarios returns exactly four scenarios."""
    assert len(Scenario.all_scenarios()) == 4
