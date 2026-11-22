"""
Acceptance tests — full project criteria.

1. Simulator reproduces exponential statistics; 100 000 blocks in under a minute.
2. Metrics table for 3 rules × 4 scenarios with plots.
3. Time-warp attack lowers Bitcoin-window difficulty while passing all timestamp
   rules; the fix stops it.
4. Every result reproducible from a seed.
"""

import time
import statistics as stats

from difficulty_timewarp.sim import Simulator, Scenario, median_time_past
from difficulty_timewarp.rules import bitcoin_window, asert, moving_average
from difficulty_timewarp.attack import TimewarpAttacker, bitcoin_window_with_fix
from difficulty_timewarp.eval import (
    mean_block_time,
    metrics_table,
    print_metrics_table,
)


# ---- helpers ----

WINDOW = 100
RULES = {
    "bitcoin_window": lambda b, ti: bitcoin_window(b, ti, window=WINDOW),
    "asert": lambda b, ti: asert(b, ti, half_life=60000.0),
    "moving_avg": lambda b, ti: moving_average(b, ti, k=50),
}
SIM = Simulator(target_interval=600.0, initial_difficulty=1.0)


# ---- 1. Exponential statistics ----

def test_exponential_statistics():
    """Mean within 1 %, median/mean ≈ 0.693."""
    def _id(b, ti):
        return b[-1].difficulty

    blocks = SIM.simulate(_id, Scenario.constant(), 100_000, seed=42)
    intervals = [blocks[i].timestamp - blocks[i - 1].timestamp for i in range(1, len(blocks))]
    mean = stats.mean(intervals)
    med = stats.median(intervals)

    assert abs(mean - 600.0) / 600.0 < 0.01
    assert 0.68 < med / mean < 0.71


def test_performance_100k():
    """100 000 blocks in under a minute."""
    def _id(b, ti):
        return b[-1].difficulty

    t0 = time.time()
    SIM.simulate(_id, Scenario.constant(), 100_000, seed=1)
    assert time.time() - t0 < 60.0


# ---- 2. Metrics table ----

def test_metrics_table_complete():
    """3 rules × 4 scenarios → 12 cells, all with positive mean time."""
    results = {}
    for rname, rule in RULES.items():
        results[rname] = {}
        for scen in Scenario.all_scenarios():
            blocks = SIM.simulate(rule, scen, 10000, seed=42)
            results[rname][scen.name] = blocks

    table = metrics_table(results, shock_block=5000)
    assert len(table) == 3
    for rname in RULES:
        assert len(table[rname]) == 4
        for scen in Scenario.all_scenarios():
            assert table[rname][scen.name]["mean_time"] > 0


# ---- 3. Time-warp attack ----

def test_attack_lowers_difficulty():
    """Attack on Bitcoin window lowers difficulty."""
    window = 50
    attacker = TimewarpAttacker(share=0.9, window=window)
    rule = lambda b, ti: bitcoin_window(b, ti, window=window)
    blocks = SIM.simulate(rule, Scenario.constant(), 10000, seed=42, attacker=attacker)
    assert blocks[-1].difficulty < blocks[0].difficulty * 0.8


def test_attack_passes_timestamp_rules():
    """Every block in the attacked chain has a valid timestamp."""
    window = 50
    attacker = TimewarpAttacker(share=0.6, window=window)
    rule = lambda b, ti: bitcoin_window(b, ti, window=window)
    blocks = SIM.simulate(rule, Scenario.constant(), 3000, seed=42, attacker=attacker)

    for i in range(11, len(blocks)):
        mtp = median_time_past(blocks, i - 1)
        assert blocks[i].timestamp > mtp


def test_fix_stops_attack():
    """With BIP-94, the attack is neutralised."""
    window = 50
    attacker = TimewarpAttacker(share=0.6, window=window)
    rule = lambda b, ti: bitcoin_window_with_fix(b, ti, window=window)
    blocks = SIM.simulate(rule, Scenario.constant(), 5000, seed=42, attacker=attacker)
    assert blocks[-1].difficulty > blocks[0].difficulty * 0.5


# ---- 4. Reproducibility ----

def test_reproducibility():
    """Same seed → identical series for every rule × scenario."""
    for rname, rule in RULES.items():
        for scen in Scenario.all_scenarios():
            a = SIM.simulate(rule, scen, 500, seed=77)
            b = SIM.simulate(rule, scen, 500, seed=77)
            for ba, bb in zip(a, b):
                assert ba.timestamp == bb.timestamp
                assert ba.difficulty == bb.difficulty
