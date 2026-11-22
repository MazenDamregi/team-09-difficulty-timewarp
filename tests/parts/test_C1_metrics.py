"""
C1 — Metrics tests.

Done when:
  - Metrics table for every rule × scenario.
  - One metric can be computed by hand from a printed series.
"""

from difficulty_timewarp.sim import Block
from difficulty_timewarp.eval import (
    mean_block_time,
    median_block_time,
    recovery_blocks,
    oscillation_amplitude,
    metrics_table,
)


def _chain(timestamps, difficulties=None):
    if difficulties is None:
        difficulties = [1.0] * len(timestamps)
    return [
        Block(height=i, timestamp=t, difficulty=d)
        for i, (t, d) in enumerate(zip(timestamps, difficulties))
    ]


def test_mean_block_time():
    """Hand-computed mean interval."""
    blocks = _chain([0, 100, 300, 600])
    # Intervals: 100, 200, 300 → mean = 200.
    assert abs(mean_block_time(blocks) - 200.0) < 1e-9


def test_median_block_time():
    """Hand-computed median interval."""
    blocks = _chain([0, 100, 300, 600])
    # Intervals: 100, 200, 300 → median = 200.
    assert abs(median_block_time(blocks) - 200.0) < 1e-9


def test_recovery_blocks_simple():
    """Difficulty returns within threshold after shock."""
    # Difficulty drops at block 5, recovers at block 10.
    diffs = [1.0] * 5 + [0.5] * 5 + [0.95] + [1.0] * 5
    blocks = _chain(list(range(len(diffs))), diffs)
    rec = recovery_blocks(blocks, target_difficulty=1.0, threshold=0.10, shock_block=5)
    assert rec == 5, f"got {rec}"  # block 10 is first within 10 %


def test_recovery_never():
    """Difficulty never recovers → returns -1."""
    diffs = [0.5] * 100
    blocks = _chain(list(range(100)), diffs)
    rec = recovery_blocks(blocks, target_difficulty=1.0, threshold=0.10, shock_block=0)
    assert rec == -1


def test_oscillation_amplitude():
    """Ratio of max to min difficulty."""
    diffs = [1.0, 2.0, 0.5, 1.5, 0.8]
    blocks = _chain(list(range(len(diffs))), diffs)
    amp = oscillation_amplitude(blocks, window=10)
    assert abs(amp - (2.0 / 0.5)) < 1e-9


def test_metrics_table():
    """metrics_table returns the expected structure."""
    blocks = _chain([i * 600.0 for i in range(100)])
    results = {"rule_a": {"constant": blocks}}
    table = metrics_table(results, target_interval=600.0, shock_block=50)
    assert "rule_a" in table
    assert "constant" in table["rule_a"]
    m = table["rule_a"]["constant"]
    assert "mean_time" in m
    assert "recovery" in m
    assert "oscillation" in m
