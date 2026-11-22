"""
A1 — Event simulator tests.

Done when:
  - Constant hash rate and fixed difficulty: mean interval within 1 % of
    expected over 100 000 blocks; median/mean ≈ 0.693.
"""

import statistics

from difficulty_timewarp.sim import Block, Simulator, Scenario


def _identity_rule(blocks, target_interval):
    """No retarget — keep difficulty constant."""
    return blocks[-1].difficulty


def test_mean_interval_within_1_percent():
    """100 000 blocks at constant difficulty → mean ≈ target_interval."""
    sim = Simulator(target_interval=600.0, initial_difficulty=1.0)
    blocks = sim.simulate(_identity_rule, Scenario.constant(1.0), 100_000, seed=42)

    intervals = [
        blocks[i].timestamp - blocks[i - 1].timestamp for i in range(1, len(blocks))
    ]
    mean = statistics.mean(intervals)
    # Within 1 % of 600.
    assert abs(mean - 600.0) / 600.0 < 0.01, f"mean = {mean}"


def test_median_over_mean():
    """Exponential distribution: median / mean ≈ ln(2) ≈ 0.693."""
    sim = Simulator(target_interval=600.0, initial_difficulty=1.0, noise_std=0.0)
    blocks = sim.simulate(_identity_rule, Scenario.constant(1.0), 100_000, seed=99)

    intervals = [
        blocks[i].timestamp - blocks[i - 1].timestamp for i in range(1, len(blocks))
    ]
    med = statistics.median(intervals)
    mean = statistics.mean(intervals)
    ratio = med / mean
    assert 0.68 < ratio < 0.71, f"median/mean = {ratio}"


def test_performance():
    """100 000 blocks must simulate in a reasonable time (< 60 s)."""
    import time

    sim = Simulator(target_interval=600.0)
    t0 = time.time()
    sim.simulate(_identity_rule, Scenario.constant(), 100_000, seed=1)
    dt = time.time() - t0
    assert dt < 60.0, f"Took {dt:.1f}s"


def test_seed_reproducibility():
    """Same seed → identical series."""
    sim = Simulator(target_interval=600.0)
    a = sim.simulate(_identity_rule, Scenario.constant(), 500, seed=77)
    b = sim.simulate(_identity_rule, Scenario.constant(), 500, seed=77)
    for ba, bb in zip(a, b):
        assert ba.timestamp == bb.timestamp
        assert ba.difficulty == bb.difficulty
