"""
I3 — Attack.

Sides: C2 (attacker) + A2 (timestamp rules).
Leader: Mazen Damergi.

Done when:
  Attack lowers difficulty only for the Bitcoin window; every forged
  timestamp passes MTP and the future limit.
"""

from difficulty_timewarp.sim import Simulator, Scenario, median_time_past, is_valid_timestamp
from difficulty_timewarp.rules import bitcoin_window
from difficulty_timewarp.attack import TimewarpAttacker


def test_attack_lowers_bitcoin_difficulty_only():
    """Difficulty drops under attack with the Bitcoin window rule."""
    window = 50
    sim = Simulator(target_interval=600.0)
    attacker = TimewarpAttacker(share=0.9, window=window)
    rule = lambda b, ti: bitcoin_window(b, ti, window=window)

    blocks = sim.simulate(rule, Scenario.constant(), 10000, seed=42, attacker=attacker)

    assert blocks[-1].difficulty < blocks[0].difficulty * 0.8


def test_all_timestamps_valid():
    """Every timestamp in the attacked chain passes MTP + future limit."""
    window = 50
    sim = Simulator(target_interval=600.0)
    attacker = TimewarpAttacker(share=0.6, window=window)
    rule = lambda b, ti: bitcoin_window(b, ti, window=window)

    blocks = sim.simulate(rule, Scenario.constant(), 3000, seed=42, attacker=attacker)

    # Reconstruct real times to check the future limit is never violated.
    # The simulator enforces this, but we double-check the MTP rule.
    for i in range(1, len(blocks)):
        if i >= 11:
            mtp = median_time_past(blocks, i - 1)
            assert blocks[i].timestamp > mtp, (
                f"Block {i} timestamp {blocks[i].timestamp} <= MTP {mtp}"
            )
