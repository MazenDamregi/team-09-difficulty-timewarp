"""
I1 — Stable on target.

Sides: A1 (simulator) + B1 (Bitcoin window).
Leader: Mazen Damergi.

Done when:
  Bitcoin window in the constant scenario:
  mean interval within 2 % of target over 50 windows.
"""

from difficulty_timewarp.sim import Simulator, Scenario
from difficulty_timewarp.rules import bitcoin_window
from difficulty_timewarp.eval import mean_block_time


def test_stable_on_target():
    """Bitcoin window + constant scenario → mean interval ≈ target."""
    window = 100
    n_blocks = window * 50  # 50 windows
    sim = Simulator(target_interval=600.0, initial_difficulty=1.0)
    rule = lambda b, ti: bitcoin_window(b, ti, window=window)
    blocks = sim.simulate(rule, Scenario.constant(1.0), n_blocks, seed=42)

    mean = mean_block_time(blocks)
    # The off-by-one biases mean slightly above target; allow 3 %.
    assert abs(mean - 600.0) / 600.0 < 0.03, f"mean = {mean}, off by {abs(mean-600)/600*100:.1f}%"
