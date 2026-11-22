"""
I4 — Fix.

Sides: C3 (BIP-94 fix) + B1 (Bitcoin window).
Leader: Mazen Damergi.

Done when:
  Attack's gain is removed; honest metrics unchanged.
"""

from difficulty_timewarp.sim import Simulator, Scenario
from difficulty_timewarp.rules import bitcoin_window
from difficulty_timewarp.attack import TimewarpAttacker, bitcoin_window_with_fix
from difficulty_timewarp.eval import mean_block_time


def test_fix_removes_attack_gain():
    """With BIP-94 fix, the attack no longer decreases difficulty."""
    window = 50
    sim = Simulator(target_interval=600.0)
    attacker = TimewarpAttacker(share=0.6, window=window)

    # With fix.
    rule = lambda b, ti: bitcoin_window_with_fix(b, ti, window=window)
    blocks = sim.simulate(rule, Scenario.constant(), 5000, seed=42, attacker=attacker)

    assert blocks[-1].difficulty > blocks[0].difficulty * 0.5, (
        f"Fix did not stop the attack: {blocks[-1].difficulty}"
    )


def test_honest_metrics_unchanged():
    """Honest scenarios produce identical results with and without the fix."""
    window = 50
    sim = Simulator(target_interval=600.0)

    rule_no = lambda b, ti: bitcoin_window(b, ti, window=window)
    rule_fx = lambda b, ti: bitcoin_window_with_fix(b, ti, window=window)

    blocks_no = sim.simulate(rule_no, Scenario.constant(), 3000, seed=42)
    blocks_fx = sim.simulate(rule_fx, Scenario.constant(), 3000, seed=42)

    mean_no = mean_block_time(blocks_no)
    mean_fx = mean_block_time(blocks_fx)
    assert abs(mean_no - mean_fx) < 1e-6, f"no_fix={mean_no}, fix={mean_fx}"
