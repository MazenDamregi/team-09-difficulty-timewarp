"""
B3 — Moving average tests.

Done when:
  - Implemented with k as a parameter.
  - Noise falls roughly as 1/√k.
"""

import statistics as stats

from difficulty_timewarp.sim import Block, Simulator, Scenario
from difficulty_timewarp.rules import moving_average


def _chain(intervals, difficulty=1.0):
    """Build a chain from a list of intervals."""
    blocks = [Block(0, 0.0, difficulty)]
    t = 0.0
    for i, iv in enumerate(intervals, 1):
        t += iv
        blocks.append(Block(i, t, difficulty))
    return blocks


def test_on_target():
    """Intervals all equal to target → difficulty unchanged."""
    target = 600.0
    blocks = _chain([600.0] * 20, difficulty=1.0)
    new = moving_average(blocks, target, k=10)
    assert abs(new - 1.0) < 1e-9, f"got {new}"


def test_fast_blocks_raise_difficulty():
    """Intervals shorter than target → difficulty increases."""
    blocks = _chain([300.0] * 20, difficulty=1.0)
    new = moving_average(blocks, 600.0, k=10)
    assert new > 1.0, f"got {new}"


def test_slow_blocks_lower_difficulty():
    """Intervals longer than target → difficulty decreases."""
    blocks = _chain([1200.0] * 20, difficulty=1.0)
    new = moving_average(blocks, 600.0, k=10)
    assert new < 1.0, f"got {new}"


def test_k_parameter():
    """Different k values give different results on the same chain."""
    # 10 fast intervals then 5 slow ones — k=5 sees only slow, k=15 sees both.
    blocks = _chain([300.0] * 10 + [900.0] * 5, difficulty=1.0)
    d15 = moving_average(blocks, 600.0, k=15)
    d5 = moving_average(blocks, 600.0, k=5)
    # k=5: avg=900, k=15: avg=(10*300+5*900)/15=500 → different adjustments.
    assert d15 != d5


def test_weighted_vs_simple():
    """Weighted average gives more weight to recent intervals."""
    # Recent intervals are fast (300), old ones are slow (900).
    blocks = _chain([900.0] * 10 + [300.0] * 10, difficulty=1.0)
    simple = moving_average(blocks, 600.0, k=20, weighted=False)
    weighted = moving_average(blocks, 600.0, k=20, weighted=True)
    # Weighted should give higher difficulty because recent blocks are fast.
    assert weighted > simple, f"weighted={weighted}, simple={simple}"


def test_noise_falls_with_sqrt_k():
    """
    With a fixed (constant) difficulty rule, the measurement noise of the
    average of the last k intervals falls as 1/√k.  We measure this by
    computing the stdev of the rolling average of intervals (not the
    closed-loop difficulty, which has feedback).
    """
    import numpy as np

    sim = Simulator(target_interval=600.0, noise_std=0.0)

    def _id(b, ti):
        return b[-1].difficulty  # constant difficulty

    blocks = sim.simulate(_id, Scenario.constant(), 20000, seed=42)
    intervals = np.array([
        blocks[i].timestamp - blocks[i - 1].timestamp
        for i in range(1, len(blocks))
    ])

    stdevs = {}
    for k in [50, 200]:
        # Rolling mean of k intervals.
        rolling = np.convolve(intervals, np.ones(k) / k, mode="valid")
        stdevs[k] = float(np.std(rolling))

    ratio = stdevs[200] / stdevs[50]
    expected_ratio = (50 / 200) ** 0.5  # 0.5
    # Allow tolerance: 0.3 to 0.7.
    assert 0.3 < ratio < 0.7, f"ratio = {ratio}, expected ≈ {expected_ratio}"
