# Team 09 — Difficulty Algorithms and the Time-Warp Attack

**Óbuda University · Introduction to Blockchain Programming**

## Team

| Role | Member                    |
|------|---------------------------|
| A    | Mazen Damergi             |
| B    | Moukthida Xaygnaphone     |
| C    | Le Khanh Hien             |

## What it does

An event-driven mining simulator that compares three difficulty-adjustment
algorithms (Bitcoin window, ASERT, moving average) under four hash-rate
scenarios, then demonstrates and fixes the time-warp attack on the
window-based rule.

## Quick start

```bash
# Install
pip install -e ".[dev]"

# Run all tests
pytest

# Run the demo (attack with and without fix, side-by-side plots)
python -m difficulty_timewarp.cli
```

## Repository layout

```
src/difficulty_timewarp/
  sim.py        — A: event simulator, timestamps, MTP, scenarios
  rules.py      — B: Bitcoin window, ASERT, moving average
  attack.py     — C: time-warp attacker and BIP-94 fix
  eval.py       — C: metrics (mean time, recovery, oscillation) and plots
  cli.py        — demo script

tests/
  parts/        — one file per part (A1–A3, B1–B3, C1–C3)
  integration/  — I1–I4
  acceptance/   — full acceptance suite

fixtures/       — shared inputs and expected outputs
docs/           — interfaces.md, report.docx, slides.pptx
```

## Checks

| Check                   | Command                           |
|-------------------------|-----------------------------------|
| All unit tests          | `pytest tests/parts/`             |
| Integration tests       | `pytest tests/integration/`       |
| Acceptance tests        | `pytest tests/acceptance/`        |
| Everything              | `pytest`                          |

## Theory question

> Why does every difficulty rule trade reaction speed for stability, and
> what does the 1/√N argument from Lab 03 say about the window size?

A difficulty rule estimates hash rate from observed block intervals. Each
interval is an exponential random variable, so any estimate from N samples
has standard deviation proportional to 1/√N. A short window (small N)
reacts quickly but oscillates; a long window is stable but slow to adjust.
The Bitcoin 2016-block window gives about 2.2 % noise (1/√2016); halving
the window doubles the noise but halves the reaction time.
