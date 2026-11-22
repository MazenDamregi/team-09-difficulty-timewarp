"""
B2 — ASERT-like per-block rule tests.

Done when:
  - Constant scenario on target.
  - After a shock, recovers within a few half-lives.
  - Rule depends only on the anchor and the latest block.
"""

import math

from difficulty_timewarp.sim import Block, Simulator, Scenario
from difficulty_timewarp.rules import asert


def _chain(heights_times, difficulty=1.0):
    return [Block(height=h, timestamp=t, difficulty=difficulty) for h, t in heights_times]


def test_constant_on_target():
    """When blocks arrive on schedule, difficulty stays at 1.0."""
    target = 600.0
    blocks = _chain([(i, i * target) for i in range(100)], difficulty=1.0)
    new = asert(blocks, target, half_life=172800.0)
    assert abs(new - 1.0) < 0.01, f"got {new}"


def test_slow_blocks_decrease_difficulty():
    """Blocks arriving late → difficulty decreases."""
    target = 600.0
    # 10 blocks, each taking 1200 s instead of 600.
    blocks = _chain([(i, i * 1200.0) for i in range(10)], difficulty=1.0)
    new = asert(blocks, target, half_life=172800.0)
    assert new < 1.0, f"expected < 1.0, got {new}"


def test_fast_blocks_increase_difficulty():
    """Blocks arriving early → difficulty increases."""
    target = 600.0
    # 10 blocks, each taking 300 s instead of 600.
    blocks = _chain([(i, i * 300.0) for i in range(10)], difficulty=1.0)
    new = asert(blocks, target, half_life=172800.0)
    assert new > 1.0, f"expected > 1.0, got {new}"


def test_depends_only_on_anchor_and_latest():
    """
    ASERT uses only the anchor (block 0) and the latest block.
    Middle blocks with different timestamps should not matter.
    """
    target = 600.0
    hl = 172800.0

    # Chain A: 0, 600, 1200, ..., 6000 (all on schedule).
    chain_a = _chain([(i, i * 600.0) for i in range(11)], difficulty=1.0)

    # Chain B: same first and last block, random middle timestamps.
    chain_b = [Block(0, 0.0, 1.0)]
    for i in range(1, 10):
        chain_b.append(Block(i, i * 999.0, 1.0))  # junk middle
    chain_b.append(Block(10, 6000.0, 1.0))

    new_a = asert(chain_a, target, half_life=hl)
    new_b = asert(chain_b, target, half_life=hl)
    assert abs(new_a - new_b) < 1e-9, f"A={new_a}, B={new_b}"


def test_recovery_after_shock():
    """After a hash-rate drop, difficulty recovers within a few half-lives."""
    sim = Simulator(target_interval=600.0)
    half_life = 60000.0
    rule = lambda b, ti: asert(b, ti, half_life=half_life)
    blocks = sim.simulate(rule, Scenario.drop_50(at_block=2000), 10000, seed=42)

    # After several half-lives worth of blocks post-shock, difficulty should adapt.
    # At half hash rate, equilibrium difficulty should be ~0.5.
    late_diffs = [b.difficulty for b in blocks[-500:]]
    mean_late = sum(late_diffs) / len(late_diffs)
    assert 0.3 < mean_late < 0.7, f"mean late difficulty = {mean_late}"


def test_half_life_math():
    """
    If time is exactly one half_life behind schedule,
    difficulty should halve: diff_new = 1.0 × 2^(−1) = 0.5.
    """
    target = 600.0
    hl = 10000.0
    # 10 blocks, ideal at 10 × 600 = 6000.  Actual time = 6000 + 10000 = 16000.
    blocks = _chain([(i, i * 600.0) for i in range(10)] + [(10, 16000.0)], difficulty=1.0)
    new = asert(blocks, target, half_life=hl)
    expected = 1.0 * math.pow(2, -(16000.0 - 11 * 600.0) / hl)
    assert abs(new - expected) < 1e-9, f"got {new}, expected {expected}"
