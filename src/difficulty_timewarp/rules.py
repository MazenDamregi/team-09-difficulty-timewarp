"""
B — Difficulty-adjustment rules.

All rules share the same signature:
    rule(blocks: list[Block], target_interval: float) -> float
returning the difficulty for the **next** block.

B1: Bitcoin window  — retarget every N blocks, 4× clamp, off-by-one.
B2: ASERT-like      — per-block exponential adjustment.
B3: Moving average  — simple and weighted.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from difficulty_timewarp.sim import Block


# ---------------------------------------------------------------------------
# B1 — Bitcoin window retarget
# ---------------------------------------------------------------------------

def bitcoin_window(
    blocks: list["Block"],
    target_interval: float = 600.0,
    *,
    window: int = 2016,
) -> float:
    """
    Bitcoin-style window retarget.

    Retargets every *window* blocks using the timestamps of the first and last
    block in the window (N−1 intervals), but divides by N × target_interval
    — the well-known off-by-one.

    The adjustment ratio is clamped to [1/4, 4].

    Returns the difficulty for the next block.
    """
    next_height = len(blocks)
    current_diff = blocks[-1].difficulty

    # Only retarget at multiples of *window*.
    if next_height < window or next_height % window != 0:
        return current_diff

    # Actual elapsed time for the last window (N−1 intervals).
    first = blocks[next_height - window]
    last = blocks[next_height - 1]
    actual_time = last.timestamp - first.timestamp

    # Expected time — Bitcoin uses N × target, NOT (N−1) × target (off-by-one).
    expected_time = window * target_interval

    # Clamp the ratio actual/expected to [1/4, 4].
    ratio = actual_time / expected_time
    ratio = max(0.25, min(4.0, ratio))

    # new_difficulty = old × (expected / actual)
    new_difficulty = current_diff / ratio
    return new_difficulty


# ---------------------------------------------------------------------------
# B2 — ASERT-like per-block rule
# ---------------------------------------------------------------------------

def asert(
    blocks: list["Block"],
    target_interval: float = 600.0,
    *,
    half_life: float = 172800.0,  # 2 days in seconds
) -> float:
    """
    ASERT-like (Absolutely Scheduled Exponential Rising Targets) per-block rule.

    target_new = target_ref × 2^((time − ideal_time) / half_life)

    Since difficulty ∝ 1/target:
        diff_new = diff_ref × 2^(−(time − ideal_time) / half_life)

    Uses block 0 as the anchor.  Recomputed every block.

    Parameters
    ----------
    half_life : float
        Seconds.  After *half_life* seconds of excess delay the difficulty
        halves; after *half_life* seconds of being ahead it doubles.
    """
    if len(blocks) < 2:
        return blocks[-1].difficulty

    anchor = blocks[0]
    latest = blocks[-1]
    next_height = len(blocks)

    ideal_time = anchor.timestamp + next_height * target_interval
    actual_time = latest.timestamp

    exponent = -(actual_time - ideal_time) / half_life
    new_difficulty = anchor.difficulty * math.pow(2, exponent)

    # Floor at a tiny positive value to avoid zero/negative difficulty.
    return max(new_difficulty, 1e-12)


# ---------------------------------------------------------------------------
# B3 — Moving average
# ---------------------------------------------------------------------------

def moving_average(
    blocks: list["Block"],
    target_interval: float = 600.0,
    *,
    k: int = 144,
    weighted: bool = False,
) -> float:
    """
    Difficulty from the (simple or weighted) average of the last *k* intervals.

    Simple:   mean of last k intervals → adjust difficulty proportionally.
    Weighted: linearly increasing weights (most recent interval has weight k).

    Noise falls roughly as 1/√k.
    """
    if len(blocks) < 2:
        return blocks[-1].difficulty

    # Gather the last k intervals.
    n = min(k, len(blocks) - 1)
    intervals = [
        blocks[-n + i].timestamp - blocks[-n + i - 1].timestamp
        for i in range(n)
    ]

    if weighted:
        weights = list(range(1, n + 1))  # 1, 2, … n
        avg = sum(w * iv for w, iv in zip(weights, intervals)) / sum(weights)
    else:
        avg = sum(intervals) / n

    # Adjust: if blocks are too fast (avg < target), increase difficulty.
    if avg <= 0:
        return blocks[-1].difficulty
    ratio = avg / target_interval
    new_difficulty = blocks[-1].difficulty / ratio
    return max(new_difficulty, 1e-12)
