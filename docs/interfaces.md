# Interfaces — Project 09: Difficulty Algorithms and the Time-Warp Attack

## Data types

### Block
```python
@dataclass
class Block:
    height: int        # 0-indexed block number
    timestamp: float   # seconds since genesis
    difficulty: float  # higher = harder to mine
```

## A → B interface

### `next_difficulty(blocks: list[Block], target_interval: float) -> float`

Given the full chain so far, return the difficulty for the **next** block.

- **Provider:** B (rules.py)
- **Consumer:** A (sim.py — the simulator calls any rule through this interface)
- **Fixture:** `fixtures/history_constant.json`

Three implementations share this signature:
| Rule             | Key parameter           |
|------------------|------------------------|
| `bitcoin_window` | `window` (default 2016)|
| `asert`          | `half_life` (seconds)  |
| `moving_average` | `k` (intervals)        |

## A → C interface

### `simulate(rule, scenario, n_blocks, seed, attacker=None) -> list[Block]`

Run the event simulator and return the full block series.

- **Provider:** A (sim.py — `Simulator.simulate`)
- **Consumer:** C (eval.py, attack.py)
- **Fixture:** `fixtures/series_drop.csv`

## C → A interface

### `TimewarpAttacker.choose_timestamp(blocks, height, real_time) -> float`

The attacker returns its preferred timestamp.  The simulator enforces
validity (MTP, future limit) after the attacker's choice.

- **Provider:** C (attack.py)
- **Consumer:** A (sim.py — passed as `attacker` argument)

## Timestamp validity (A2)

A timestamp is valid iff:
1. `timestamp > median_time_past(last 11 blocks)`  — strictly greater
2. `timestamp <= real_time + 7200`  — at most 2 hours ahead

## BIP-94 fix (C3)

The first block of a new difficulty window may not be timestamped more than
600 seconds before the last block of the previous window:
```
blocks[window_start].timestamp >= blocks[window_start - 1].timestamp - 600
```
