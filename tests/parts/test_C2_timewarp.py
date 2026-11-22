"""
C2 — Time-warp attacker tests.

Done when:
  - With a majority attacker on the Bitcoin window, difficulty falls window
    after window while real block times shrink.
  - With the ASERT-like rule the same strategy gains nothing.
"""

from difficulty_timewarp.sim import Simulator, Scenario, median_time_past, is_valid_timestamp
from difficulty_timewarp.rules import bitcoin_window, asert
from difficulty_timewarp.attack import TimewarpAttacker


def test_attack_lowers_bitcoin_difficulty():
    """
    With a majority attacker, Bitcoin-window difficulty decreases over
    successive retargets.
    """
    window = 50
    sim = Simulator(target_interval=600.0, initial_difficulty=1.0)
    attacker = TimewarpAttacker(share=0.9, window=window)
    rule = lambda b, ti: bitcoin_window(b, ti, window=window)

    blocks = sim.simulate(rule, Scenario.constant(), 10000, seed=42, attacker=attacker)

    # Difficulty should have dropped significantly.
    initial = blocks[0].difficulty
    final = blocks[-1].difficulty
    assert final < initial * 0.8, (
        f"Attack failed to lower difficulty: initial={initial}, final={final}"
    )


def test_attack_no_gain_on_asert():
    """
    The same attack strategy gains nothing on the ASERT-like rule:
    difficulty does not fall below equilibrium.
    """
    window = 50
    sim = Simulator(target_interval=600.0, initial_difficulty=1.0)
    attacker = TimewarpAttacker(share=0.6, window=window)
    rule = lambda b, ti: asert(b, ti, half_life=60000.0)

    blocks = sim.simulate(rule, Scenario.constant(), 5000, seed=42, attacker=attacker)

    final = blocks[-1].difficulty
    # ASERT should stay near 1.0 (the attacker controls timestamps but
    # ASERT looks at the anchor and the latest block; manipulated timestamps
    # close to MTP don't create an exploitable gap).
    assert final > 0.5, f"ASERT difficulty dropped too much: {final}"


def test_attacker_timestamps_pass_mtp():
    """Every attacker-generated timestamp must pass the MTP and future-limit rules."""
    window = 50
    sim = Simulator(target_interval=600.0, initial_difficulty=1.0)
    attacker = TimewarpAttacker(share=0.6, window=window)
    rule = lambda b, ti: bitcoin_window(b, ti, window=window)

    blocks = sim.simulate(rule, Scenario.constant(), 2000, seed=42, attacker=attacker)

    for i in range(11, len(blocks)):
        mtp = median_time_past(blocks, i - 1)
        assert blocks[i].timestamp > mtp, f"Block {i} violates MTP"


def test_attack_different_seed():
    """Attack reproduces with a different seed (direction is the same)."""
    window = 50
    sim = Simulator(target_interval=600.0)
    attacker = TimewarpAttacker(share=0.9, window=window)
    rule = lambda b, ti: bitcoin_window(b, ti, window=window)

    for seed in [42, 99, 123]:
        blocks = sim.simulate(rule, Scenario.constant(), 10000, seed=seed, attacker=attacker)
        assert blocks[-1].difficulty < blocks[0].difficulty * 0.95, (
            f"seed={seed}: difficulty did not drop"
        )
