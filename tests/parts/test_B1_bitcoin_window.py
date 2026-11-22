"""
B1 — Bitcoin window retarget tests.

Done when:
  - Retarget values 2000 / 500 / 4000 / 250 from difficulty 1000.
  - Constant scenario stays on target.
  - Off-by-one checked with a 4-block window by hand.
"""

from difficulty_timewarp.sim import Block
from difficulty_timewarp.rules import bitcoin_window


def _blocks_with_times(timestamps, difficulty=1000.0):
    """Build a chain at constant difficulty with given timestamps."""
    return [Block(height=i, timestamp=t, difficulty=difficulty) for i, t in enumerate(timestamps)]


def test_retarget_doubles():
    """Blocks twice as fast → difficulty doubles (1000 → 2000)."""
    # Window of 4.  Expected time = 4 × 600 = 2400 (off-by-one: only 3 intervals).
    # Actual 3 intervals, each 300 → actual = 900.
    # ratio = 900 / 2400 = 0.375 → new = 1000 / 0.375 = 2666.67
    #
    # Hmm, let's use exact values.
    # For doubling: ratio = 0.5 → actual/expected = 0.5 → new = 1000 / 0.5 = 2000.
    # actual = 0.5 × expected = 0.5 × 4 × 600 = 1200.
    # With 3 intervals: each = 400.
    window = 4
    target_interval = 600.0
    expected = window * target_interval  # 2400
    actual = expected * 0.5  # 1200 → 3 intervals of 400
    t0 = 0
    timestamps = [t0 + i * (actual / (window - 1)) for i in range(window)]
    blocks = _blocks_with_times(timestamps, difficulty=1000.0)
    new = bitcoin_window(blocks, target_interval, window=window)
    assert abs(new - 2000.0) < 1e-6, f"got {new}"


def test_retarget_halves():
    """Blocks twice as slow → difficulty halves (1000 → 500)."""
    window = 4
    target_interval = 600.0
    expected = window * target_interval
    actual = expected * 2.0  # 4800
    timestamps = [i * (actual / (window - 1)) for i in range(window)]
    blocks = _blocks_with_times(timestamps, difficulty=1000.0)
    new = bitcoin_window(blocks, target_interval, window=window)
    assert abs(new - 500.0) < 1e-6, f"got {new}"


def test_retarget_clamp_up():
    """Way too fast → clamped to 4× (1000 → 4000)."""
    window = 4
    target_interval = 600.0
    expected = window * target_interval
    actual = expected * 0.1  # Very short
    timestamps = [i * (actual / (window - 1)) for i in range(window)]
    blocks = _blocks_with_times(timestamps, difficulty=1000.0)
    new = bitcoin_window(blocks, target_interval, window=window)
    assert abs(new - 4000.0) < 1e-6, f"got {new}"


def test_retarget_clamp_down():
    """Way too slow → clamped to 1/4 (1000 → 250)."""
    window = 4
    target_interval = 600.0
    expected = window * target_interval
    actual = expected * 10.0  # Very long
    timestamps = [i * (actual / (window - 1)) for i in range(window)]
    blocks = _blocks_with_times(timestamps, difficulty=1000.0)
    new = bitcoin_window(blocks, target_interval, window=window)
    assert abs(new - 250.0) < 1e-6, f"got {new}"


def test_no_retarget_between_windows():
    """Difficulty unchanged between retarget points."""
    window = 4
    blocks = _blocks_with_times([0, 600, 1200], difficulty=1000.0)
    # Only 3 blocks → not at a retarget point.
    new = bitcoin_window(blocks, 600.0, window=window)
    assert new == 1000.0


def test_constant_stays_on_target():
    """
    With constant hash rate and difficulty-adjusted rule, the difficulty
    stays approximately at the initial value.
    """
    from difficulty_timewarp.sim import Simulator, Scenario

    window = 100
    sim = Simulator(target_interval=600.0, initial_difficulty=1.0)
    rule = lambda b, ti: bitcoin_window(b, ti, window=window)
    blocks = sim.simulate(rule, Scenario.constant(1.0), 5000, seed=42)

    # After several retargets, difficulty should still be near 1.0.
    final_diffs = [b.difficulty for b in blocks[-500:]]
    mean_diff = sum(final_diffs) / len(final_diffs)
    assert 0.8 < mean_diff < 1.2, f"mean difficulty = {mean_diff}"


def test_off_by_one_4_block_window():
    """
    With a 4-block window, the off-by-one is visible:
    4 blocks have 3 intervals, but expected uses 4 × target.
    With constant 600s intervals: actual = 3 × 600 = 1800,
    expected = 4 × 600 = 2400, ratio = 0.75, new = 1000 / 0.75 = 1333.33.
    Without off-by-one (expected = 3 × 600): ratio = 1.0, new = 1000.
    """
    window = 4
    target_interval = 600.0
    timestamps = [i * 600.0 for i in range(window)]  # 0, 600, 1200, 1800
    blocks = _blocks_with_times(timestamps, difficulty=1000.0)
    new = bitcoin_window(blocks, target_interval, window=window)
    # actual = 1800, expected = 2400, ratio = 0.75, new = 1333.33
    expected_new = 1000.0 / (1800.0 / 2400.0)
    assert abs(new - expected_new) < 1e-6, f"got {new}, expected {expected_new}"
    # This proves the off-by-one: without it, new would be 1000.
    assert new > 1000.0, "Off-by-one should push difficulty UP with equal intervals"
