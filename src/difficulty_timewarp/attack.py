"""
C2/C3 — Time-warp attacker and BIP-94 fix.

C2: TimewarpAttacker — sets timestamps as low as MTP allows, except the last
    block of each difficulty window, which it sets far ahead within the future
    limit.  With a majority attacker on the Bitcoin window, difficulty falls
    window after window while real block times shrink.

C3: bip94_check — the first block of a new window may not be timestamped more
    than 600 s before the last block of the previous window (Testnet4 fix).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from difficulty_timewarp.sim import median_time_past

if TYPE_CHECKING:
    from difficulty_timewarp.sim import Block


class TimewarpAttacker:
    """
    An attacker with *share* of the total hash rate that manipulates timestamps
    to exploit the Bitcoin-window retarget rule.

    Strategy
    --------
    - Most blocks: set timestamp as LOW as MTP + 1 (minimum valid).
    - Last block of each difficulty window: set timestamp as HIGH as
      real_time + future_limit (maximum valid).

    This makes the difficulty window appear to span a very long time,
    tricking the retarget into lowering difficulty.
    """

    def __init__(
        self,
        share: float = 0.51,
        window: int = 2016,
        future_limit: float = 7200.0,
    ):
        self.share = share
        self.window = window
        self.future_limit = future_limit

    def choose_timestamp(
        self,
        blocks: list["Block"],
        height: int,
        real_time: float,
    ) -> float:
        """
        Return the attacker's chosen timestamp for block at *height*.

        The timestamp will later be clamped by enforce_timestamp, so we only
        need to express intent; validity is enforced by the simulator.
        """
        # Is this the last block of a difficulty window?
        is_last_in_window = (height + 1) % self.window == 0

        if is_last_in_window:
            # Push timestamp as far into the future as allowed.
            return real_time + self.future_limit
        else:
            # Push timestamp as low as allowed (MTP + 1).
            if len(blocks) >= 1:
                mtp = median_time_past(blocks)
                return mtp + 1
            return 0.0


# ---------------------------------------------------------------------------
# C3 — BIP-94 style fix
# ---------------------------------------------------------------------------

def bip94_check(
    blocks: list["Block"],
    window: int = 2016,
    max_rewind: float = 600.0,
) -> bool:
    """
    BIP-94 (Testnet4) time-warp fix.

    The first block of a new difficulty window may NOT be timestamped more
    than *max_rewind* seconds before the last block of the previous window.

    Returns True if the timestamp is **valid** (passes the check).
    Returns True trivially if we are not at a window boundary.
    """
    height = blocks[-1].height
    if height < window:
        return True

    # Are we the first block of a new window?
    if height % window != 0:
        return True

    last_prev_window = blocks[-2]  # block at height − 1 (last of prev window)
    first_new_window = blocks[-1]  # this block (first of new window)

    return first_new_window.timestamp >= last_prev_window.timestamp - max_rewind


def bitcoin_window_with_fix(
    blocks: list["Block"],
    target_interval: float = 600.0,
    *,
    window: int = 2016,
    max_rewind: float = 600.0,
) -> float:
    """
    Bitcoin window retarget with the BIP-94 timestamp check applied.

    If the latest block violates the BIP-94 rule, its timestamp is adjusted
    upward before the difficulty calculation proceeds.  In practice a node
    would reject the block; in simulation we clamp and continue.
    """
    from difficulty_timewarp.rules import bitcoin_window as _btc

    # Enforce BIP-94 on the latest block before retarget.
    latest = blocks[-1]
    if latest.height >= window and latest.height % window == 0:
        prev_last = blocks[-2]
        min_ts = prev_last.timestamp - max_rewind
        if latest.timestamp < min_ts:
            # Clamp timestamp up (simulate rejection / correction).
            blocks = list(blocks)  # shallow copy
            from difficulty_timewarp.sim import Block
            blocks[-1] = Block(
                height=latest.height,
                timestamp=min_ts,
                difficulty=latest.difficulty,
            )

    return _btc(blocks, target_interval, window=window)
