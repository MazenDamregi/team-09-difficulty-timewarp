"""
A — Event simulator, timestamp rules, and scenarios.

A1: Event simulator  — block intervals ~ Exponential(mean = difficulty/hashrate * target_interval).
A2: Timestamp rules  — MTP (median of last 11), 2-hour future limit.
A3: Scenarios        — constant, −50 % drop, ×3 jump, slow ramp; seeded.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from typing import Callable, Optional, Protocol

import numpy as np


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------

@dataclass
class Block:
    """One block in the simulated chain."""
    height: int
    timestamp: float
    difficulty: float


# ---------------------------------------------------------------------------
# A2 — Timestamp rules
# ---------------------------------------------------------------------------

def median_time_past(blocks: list[Block], index: int | None = None) -> float:
    """
    Median-Time-Past: median timestamp of the previous 11 blocks.

    If fewer than 11 blocks exist before *index*, use all available.
    *index* defaults to the last block in the list.
    """
    if index is None:
        index = len(blocks) - 1
    start = max(0, index - 10)  # 11 blocks: index-10 .. index
    window = [blocks[i].timestamp for i in range(start, index + 1)]
    return statistics.median(window)


def is_valid_timestamp(
    timestamp: float,
    blocks: list[Block],
    real_time: float,
    future_limit: float = 7200.0,
) -> bool:
    """
    A timestamp is valid iff:
      1. It is strictly greater than the MTP of the chain so far.
      2. It is at most *future_limit* seconds ahead of *real_time*.
    """
    if len(blocks) >= 1:
        mtp = median_time_past(blocks)
        if timestamp <= mtp:
            return False
    if timestamp > real_time + future_limit:
        return False
    return True


def enforce_timestamp(
    timestamp: float,
    blocks: list[Block],
    real_time: float,
    future_limit: float = 7200.0,
) -> float:
    """Clamp *timestamp* into the valid range [MTP + 1, real_time + future_limit]."""
    if len(blocks) >= 1:
        mtp = median_time_past(blocks)
        timestamp = max(timestamp, mtp + 1)
    timestamp = min(timestamp, real_time + future_limit)
    return timestamp


# ---------------------------------------------------------------------------
# A3 — Scenarios (hash-rate schedules)
# ---------------------------------------------------------------------------

class Scenario:
    """
    A hash-rate schedule: returns the hash rate at a given block height.

    All scenarios are deterministic (no randomness of their own).
    """

    def __init__(self, name: str, fn: Callable[[int], float]):
        self.name = name
        self._fn = fn

    def hashrate_at(self, height: int) -> float:
        return self._fn(height)

    def __repr__(self) -> str:
        return f"Scenario({self.name!r})"

    # ---- factory methods ----

    @staticmethod
    def constant(hashrate: float = 1.0) -> "Scenario":
        """Constant hash rate."""
        return Scenario("constant", lambda h: hashrate)

    @staticmethod
    def drop_50(at_block: int = 5000, hashrate: float = 1.0) -> "Scenario":
        """Hash rate drops by 50 % at *at_block*."""
        return Scenario(
            "drop_50",
            lambda h: hashrate if h < at_block else hashrate * 0.5,
        )

    @staticmethod
    def jump_3x(at_block: int = 5000, hashrate: float = 1.0) -> "Scenario":
        """Hash rate triples at *at_block*."""
        return Scenario(
            "jump_3x",
            lambda h: hashrate if h < at_block else hashrate * 3.0,
        )

    @staticmethod
    def slow_ramp(
        start_rate: float = 1.0,
        end_rate: float = 3.0,
        over_blocks: int = 20000,
    ) -> "Scenario":
        """Hash rate ramps linearly from *start_rate* to *end_rate*."""
        return Scenario(
            "slow_ramp",
            lambda h: start_rate + (end_rate - start_rate) * min(h / over_blocks, 1.0),
        )

    @staticmethod
    def all_scenarios() -> list["Scenario"]:
        """Return the four standard scenarios."""
        return [
            Scenario.constant(),
            Scenario.drop_50(),
            Scenario.jump_3x(),
            Scenario.slow_ramp(),
        ]


# ---------------------------------------------------------------------------
# A1 — Event simulator
# ---------------------------------------------------------------------------

# Protocol for difficulty rules so the simulator is rule-agnostic.
class DifficultyRule(Protocol):
    def __call__(self, blocks: list[Block], target_interval: float) -> float: ...


class Simulator:
    """
    Discrete-event mining simulator.

    Each block interval is drawn from Exponential(mean = difficulty / hashrate × target_interval).
    No real hashing is performed.
    """

    def __init__(
        self,
        target_interval: float = 600.0,
        initial_difficulty: float = 1.0,
        noise_std: float = 1.0,
        future_limit: float = 7200.0,
    ):
        self.target_interval = target_interval
        self.initial_difficulty = initial_difficulty
        self.noise_std = noise_std
        self.future_limit = future_limit

    def simulate(
        self,
        rule: DifficultyRule,
        scenario: Scenario,
        n_blocks: int,
        seed: int = 42,
        attacker: Optional["_AttackerProtocol"] = None,
    ) -> list[Block]:
        """
        Simulate *n_blocks* under *rule* and *scenario*.

        Parameters
        ----------
        rule : callable(blocks, target_interval) -> float
            Returns the difficulty for the next block.
        scenario : Scenario
            Hash-rate schedule.
        n_blocks : int
            How many blocks to mine.
        seed : int
            Random seed for reproducibility.
        attacker : optional
            Object with .share (float) and .choose_timestamp(blocks, height, real_time) -> float.

        Returns
        -------
        list[Block]
        """
        rng = np.random.default_rng(seed)
        blocks: list[Block] = []
        difficulty = self.initial_difficulty
        real_time = 0.0

        for height in range(n_blocks):
            # --- mine the block ---
            if height > 0:
                hashrate = scenario.hashrate_at(height)
                mean_interval = difficulty * self.target_interval / hashrate
                interval = float(rng.exponential(mean_interval))
                real_time += interval

            # --- choose timestamp ---
            if height == 0:
                timestamp = 0.0
            elif attacker is not None and rng.random() < attacker.share:
                # Attacker-mined block: attacker picks the timestamp.
                timestamp = attacker.choose_timestamp(blocks, height, real_time)
            else:
                # Honest miner: real time + small noise.
                timestamp = real_time + float(rng.normal(0, self.noise_std))

            # Enforce validity.
            timestamp = enforce_timestamp(
                timestamp, blocks, real_time, self.future_limit
            )

            block = Block(height=height, timestamp=timestamp, difficulty=difficulty)
            blocks.append(block)

            # --- difficulty for the NEXT block ---
            difficulty = rule(blocks, self.target_interval)

        return blocks


class _AttackerProtocol(Protocol):
    share: float
    def choose_timestamp(
        self, blocks: list[Block], height: int, real_time: float
    ) -> float: ...
