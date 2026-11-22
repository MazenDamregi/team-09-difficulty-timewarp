"""
Demo CLI — run the attack with and without the fix, produce plots.

Usage:
    python -m difficulty_timewarp.cli
"""

from __future__ import annotations

import time

from difficulty_timewarp.sim import Simulator, Scenario
from difficulty_timewarp.rules import bitcoin_window, asert, moving_average
from difficulty_timewarp.attack import TimewarpAttacker, bitcoin_window_with_fix
from difficulty_timewarp.eval import (
    metrics_table,
    print_metrics_table,
    plot_difficulty,
    plot_attack_comparison,
    mean_block_time,
)


def run_metrics_demo(n_blocks: int = 15000, seed: int = 42) -> None:
    """Run all rules × all scenarios and print the metrics table."""
    sim = Simulator(target_interval=600.0)
    scenarios = Scenario.all_scenarios()

    # Use a smaller window so retargets happen within our block count.
    window = 100
    rules = {
        "bitcoin_window": lambda b, ti: bitcoin_window(b, ti, window=window),
        "asert": lambda b, ti: asert(b, ti, half_life=60000.0),
        "moving_avg_k50": lambda b, ti: moving_average(b, ti, k=50),
    }

    results: dict[str, dict[str, list]] = {}
    for rname, rule in rules.items():
        results[rname] = {}
        for scen in scenarios:
            t0 = time.time()
            blocks = sim.simulate(rule, scen, n_blocks, seed=seed)
            dt = time.time() - t0
            results[rname][scen.name] = blocks
            print(f"  {rname:20s} × {scen.name:12s}  {n_blocks} blocks in {dt:.2f}s")

    table = metrics_table(results)
    print("\n" + print_metrics_table(table))

    # Plot one scenario per rule.
    for scen in scenarios:
        series = {rname: results[rname][scen.name] for rname in rules}
        plot_difficulty(series, title=f"Difficulty — {scen.name}", save_path=f"difficulty_{scen.name}.png")
        print(f"  Saved difficulty_{scen.name}.png")


def run_attack_demo(n_blocks: int = 15000, seed: int = 42) -> None:
    """Demonstrate the time-warp attack with and without the BIP-94 fix."""
    window = 100
    sim = Simulator(target_interval=600.0)
    scenario = Scenario.constant()
    attacker = TimewarpAttacker(share=0.51, window=window)

    # Without fix.
    rule_no_fix = lambda b, ti: bitcoin_window(b, ti, window=window)
    blocks_no_fix = sim.simulate(rule_no_fix, scenario, n_blocks, seed=seed, attacker=attacker)
    print(f"  Without fix: final difficulty = {blocks_no_fix[-1].difficulty:.6f}")
    print(f"               mean block time  = {mean_block_time(blocks_no_fix):.1f}s")

    # With fix.
    rule_fix = lambda b, ti: bitcoin_window_with_fix(b, ti, window=window, max_rewind=600.0)
    blocks_fix = sim.simulate(rule_fix, scenario, n_blocks, seed=seed, attacker=attacker)
    print(f"  With fix:    final difficulty = {blocks_fix[-1].difficulty:.6f}")
    print(f"               mean block time  = {mean_block_time(blocks_fix):.1f}s")

    plot_attack_comparison(blocks_no_fix, blocks_fix, save_path="attack_comparison.png")
    print("  Saved attack_comparison.png")


def main() -> None:
    print("=" * 60)
    print("Project 09 — Difficulty Algorithms and the Time-Warp Attack")
    print("=" * 60)

    print("\n--- Metrics demo (3 rules × 4 scenarios) ---")
    run_metrics_demo()

    print("\n--- Time-warp attack demo ---")
    run_attack_demo()

    print("\nDone.")


if __name__ == "__main__":
    main()
