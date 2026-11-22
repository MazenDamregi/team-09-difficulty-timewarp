"""
C3 — BIP-94 fix tests.

Done when:
  - With the fix, the attack stops lowering difficulty.
  - Honest scenarios unchanged by the fix.
"""

from difficulty_timewarp.sim import Block, Simulator, Scenario
from difficulty_timewarp.rules import bitcoin_window
from difficulty_timewarp.attack import (
    TimewarpAttacker,
    bip94_check,
    bitcoin_window_with_fix,
)


def test_bip94_accepts_honest():
    """Honest blocks never violate BIP-94."""
    window = 50
    sim = Simulator(target_interval=600.0)
    rule = lambda b, ti: bitcoin_window(b, ti, window=window)
    blocks = sim.simulate(rule, Scenario.constant(), 2000, seed=42)

    for i in range(window, len(blocks)):
        # Check every block that starts a new window.
        if blocks[i].height % window == 0:
            chain_up_to = blocks[: i + 1]
            assert bip94_check(chain_up_to, window=window), (
                f"Honest block {i} failed BIP-94"
            )


def test_bip94_rejects_attack():
    """
    At least some attacker-produced window boundaries violate BIP-94.
    """
    window = 50
    sim = Simulator(target_interval=600.0)
    attacker = TimewarpAttacker(share=0.6, window=window)
    rule = lambda b, ti: bitcoin_window(b, ti, window=window)
    blocks = sim.simulate(rule, Scenario.constant(), 2000, seed=42, attacker=attacker)

    violations = 0
    for i in range(window, len(blocks)):
        if blocks[i].height % window == 0:
            chain_up_to = blocks[: i + 1]
            if not bip94_check(chain_up_to, window=window):
                violations += 1

    assert violations > 0, "Expected at least one BIP-94 violation from the attacker"


def test_fix_stops_difficulty_drop():
    """With the BIP-94 fix, the attack no longer lowers difficulty."""
    window = 50
    sim = Simulator(target_interval=600.0)
    attacker = TimewarpAttacker(share=0.6, window=window)
    rule_fix = lambda b, ti: bitcoin_window_with_fix(b, ti, window=window)

    blocks = sim.simulate(rule_fix, Scenario.constant(), 5000, seed=42, attacker=attacker)

    final = blocks[-1].difficulty
    initial = blocks[0].difficulty
    # Difficulty should NOT have dropped significantly.
    assert final > initial * 0.5, (
        f"Fix failed: difficulty still dropped from {initial} to {final}"
    )


def test_fix_does_not_hurt_honest():
    """The fix does not change results for honest scenarios."""
    window = 50
    sim = Simulator(target_interval=600.0)

    rule_no_fix = lambda b, ti: bitcoin_window(b, ti, window=window)
    rule_fix = lambda b, ti: bitcoin_window_with_fix(b, ti, window=window)

    for scen in Scenario.all_scenarios():
        blocks_no = sim.simulate(rule_no_fix, scen, 3000, seed=42)
        blocks_fix = sim.simulate(rule_fix, scen, 3000, seed=42)

        # Difficulty series should be identical for honest miners.
        for a, b in zip(blocks_no, blocks_fix):
            assert abs(a.difficulty - b.difficulty) < 1e-9, (
                f"Scenario {scen.name}, block {a.height}: "
                f"no_fix={a.difficulty}, fix={b.difficulty}"
            )
