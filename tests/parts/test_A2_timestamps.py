"""
A2 — Timestamp rules tests.

Done when:
  - Blocks violating MTP or the future limit are rejected.
  - Honest noise never violates them.
  - A timestamp exactly at the MTP is rejected (must be strictly greater).
"""

from difficulty_timewarp.sim import Block, median_time_past, is_valid_timestamp, enforce_timestamp


def _chain(timestamps):
    """Build a list of blocks from timestamps."""
    return [Block(height=i, timestamp=t, difficulty=1.0) for i, t in enumerate(timestamps)]


def test_mtp_basic():
    """MTP of 11 blocks is the median timestamp."""
    blocks = _chain([100, 110, 105, 115, 120, 108, 125, 130, 112, 135, 140])
    # Sorted: 100, 105, 108, 110, 112, 115, 120, 125, 130, 135, 140
    # Median = 115
    assert median_time_past(blocks) == 115.0


def test_mtp_fewer_than_11():
    """MTP with fewer than 11 blocks uses all available."""
    blocks = _chain([10, 20, 30])
    assert median_time_past(blocks) == 20.0


def test_timestamp_at_mtp_rejected():
    """A timestamp exactly equal to MTP must be rejected (strictly greater)."""
    blocks = _chain([100, 110, 105, 115, 120, 108, 125, 130, 112, 135, 140])
    mtp = median_time_past(blocks)  # 115
    assert not is_valid_timestamp(mtp, blocks, real_time=200.0)


def test_timestamp_above_mtp_accepted():
    """A timestamp just above MTP is accepted."""
    blocks = _chain([100, 110, 105, 115, 120, 108, 125, 130, 112, 135, 140])
    mtp = median_time_past(blocks)
    assert is_valid_timestamp(mtp + 1, blocks, real_time=200.0)


def test_future_limit_exceeded():
    """A timestamp more than 2 hours ahead is rejected."""
    blocks = _chain([100])
    assert not is_valid_timestamp(100 + 7201, blocks, real_time=100.0)


def test_future_limit_ok():
    """A timestamp exactly at the future limit is accepted."""
    blocks = _chain([100])
    assert is_valid_timestamp(100 + 7200, blocks, real_time=100.0)


def test_enforce_clamps_low():
    """enforce_timestamp clamps up to MTP + 1."""
    blocks = _chain([100, 110, 105, 115, 120, 108, 125, 130, 112, 135, 140])
    mtp = median_time_past(blocks)  # 115
    result = enforce_timestamp(50.0, blocks, real_time=200.0)
    assert result == mtp + 1


def test_enforce_clamps_high():
    """enforce_timestamp clamps down to real_time + future_limit."""
    blocks = _chain([100])
    result = enforce_timestamp(99999.0, blocks, real_time=100.0)
    assert result == 100.0 + 7200.0


def test_honest_noise_never_violates():
    """Simulated honest blocks never violate timestamp rules."""
    from difficulty_timewarp.sim import Simulator, Scenario

    def _id_rule(blocks, ti):
        return blocks[-1].difficulty

    sim = Simulator(target_interval=600.0, noise_std=1.0)
    blocks = sim.simulate(_id_rule, Scenario.constant(), 5000, seed=42)

    for i in range(11, len(blocks)):
        mtp = median_time_past(blocks, i - 1)
        assert blocks[i].timestamp > mtp, f"Block {i} violates MTP"
