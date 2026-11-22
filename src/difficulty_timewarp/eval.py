"""
C1 — Metrics and plotting.

mean_block_time        — average interval across the series.
recovery_blocks        — blocks until difficulty returns within 10 % of target.
oscillation_amplitude  — peak-to-trough ratio of difficulty.
metrics_table          — all metrics for every rule × scenario combination.
plot_difficulty         — difficulty-over-height chart (requires matplotlib).
"""

from __future__ import annotations

import statistics
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from difficulty_timewarp.sim import Block


# ---------------------------------------------------------------------------
# C1 — Metrics
# ---------------------------------------------------------------------------

def mean_block_time(blocks: list["Block"]) -> float:
    """Mean interval between consecutive blocks."""
    if len(blocks) < 2:
        return 0.0
    intervals = [
        blocks[i].timestamp - blocks[i - 1].timestamp
        for i in range(1, len(blocks))
    ]
    return statistics.mean(intervals)


def median_block_time(blocks: list["Block"]) -> float:
    """Median interval between consecutive blocks."""
    if len(blocks) < 2:
        return 0.0
    intervals = [
        blocks[i].timestamp - blocks[i - 1].timestamp
        for i in range(1, len(blocks))
    ]
    return statistics.median(intervals)


def recovery_blocks(
    blocks: list["Block"],
    target_difficulty: float = 1.0,
    threshold: float = 0.10,
    shock_block: int = 0,
) -> int:
    """
    Number of blocks after *shock_block* until the difficulty stays
    within *threshold* (fraction) of *target_difficulty*.

    Returns -1 if it never recovers within the series.
    """
    lo = target_difficulty * (1 - threshold)
    hi = target_difficulty * (1 + threshold)

    for i in range(shock_block, len(blocks)):
        if lo <= blocks[i].difficulty <= hi:
            return i - shock_block
    return -1


def oscillation_amplitude(blocks: list["Block"], window: int = 500) -> float:
    """
    Ratio of max to min difficulty in the last *window* blocks.
    A value of 1.0 means no oscillation.
    """
    if len(blocks) < 2:
        return 1.0
    tail = blocks[-window:]
    diffs = [b.difficulty for b in tail]
    mn = min(diffs)
    if mn <= 0:
        return float("inf")
    return max(diffs) / mn


def metrics_table(
    results: dict[str, dict[str, list["Block"]]],
    target_interval: float = 600.0,
    shock_block: int = 5000,
) -> dict[str, dict[str, dict[str, float]]]:
    """
    Compute all metrics for every rule × scenario.

    Parameters
    ----------
    results : dict[rule_name][scenario_name] -> list[Block]
    target_interval : float
    shock_block : int
        Block height where hash-rate shocks happen.

    Returns
    -------
    dict[rule_name][scenario_name] -> {"mean_time", "recovery", "oscillation"}
    """
    table: dict[str, dict[str, dict[str, float]]] = {}

    for rule_name, scenarios in results.items():
        table[rule_name] = {}
        for scen_name, blocks in scenarios.items():
            table[rule_name][scen_name] = {
                "mean_time": mean_block_time(blocks),
                "recovery": recovery_blocks(
                    blocks,
                    target_difficulty=1.0,
                    threshold=0.10,
                    shock_block=shock_block,
                ),
                "oscillation": oscillation_amplitude(blocks),
            }

    return table


def print_metrics_table(table: dict) -> str:
    """Pretty-print the metrics table."""
    lines = []
    header = f"{'Rule':<20} {'Scenario':<15} {'Mean time':>10} {'Recovery':>10} {'Oscillation':>12}"
    lines.append(header)
    lines.append("-" * len(header))
    for rule_name, scenarios in table.items():
        for scen_name, m in scenarios.items():
            rec = str(int(m["recovery"])) if m["recovery"] >= 0 else "never"
            lines.append(
                f"{rule_name:<20} {scen_name:<15} {m['mean_time']:>10.1f} {rec:>10} {m['oscillation']:>12.3f}"
            )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Plotting (optional — requires matplotlib)
# ---------------------------------------------------------------------------

def plot_difficulty(
    series_dict: dict[str, list["Block"]],
    title: str = "Difficulty over height",
    save_path: str | None = None,
) -> None:
    """
    Plot difficulty vs height for one or more series.

    Parameters
    ----------
    series_dict : dict[label] -> list[Block]
    title : str
    save_path : str or None
        If given, save to file instead of showing.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(12, 5))
    for label, blocks in series_dict.items():
        heights = [b.height for b in blocks]
        diffs = [b.difficulty for b in blocks]
        ax.plot(heights, diffs, label=label, linewidth=0.8)
    ax.set_xlabel("Block height")
    ax.set_ylabel("Difficulty")
    ax.set_title(title)
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150)
        plt.close(fig)
    else:
        plt.close(fig)


def plot_attack_comparison(
    without_fix: list["Block"],
    with_fix: list["Block"],
    title: str = "Time-warp attack: with and without BIP-94 fix",
    save_path: str | None = None,
) -> None:
    """Side-by-side difficulty plot for the attack demo."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5), sharey=False)

    h1 = [b.height for b in without_fix]
    d1 = [b.difficulty for b in without_fix]
    ax1.plot(h1, d1, color="crimson", linewidth=0.8)
    ax1.set_title("Without fix")
    ax1.set_xlabel("Block height")
    ax1.set_ylabel("Difficulty")
    ax1.grid(True, alpha=0.3)

    h2 = [b.height for b in with_fix]
    d2 = [b.difficulty for b in with_fix]
    ax2.plot(h2, d2, color="steelblue", linewidth=0.8)
    ax2.set_title("With BIP-94 fix")
    ax2.set_xlabel("Block height")
    ax2.set_ylabel("Difficulty")
    ax2.grid(True, alpha=0.3)

    fig.suptitle(title, fontsize=13, fontweight="bold")
    fig.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150)
        plt.close(fig)
    else:
        plt.close(fig)
