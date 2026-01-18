# Developer Tools

This directory contains development and debugging scripts that are not part of the core simulation or backend.

## Solution Capture Scripts

Scripts for running long simulations and capturing evolved poker solutions:

| Script | Description |
|--------|-------------|
| `capture_antigravity_solution_v3.py` | Capture evolved solution with tuned parameters |
| `capture_gpt5_prime_solution.py` | GPT-5 configuration capture |
| `capture_haiku_solution.py` | Standard Haiku solution capture |
| `capture_haiku_solution_100k.py` | Extended 100k frame Haiku capture |
| `capture_sonnet_solution.py` | Sonnet configuration capture |

## Tournament & Evaluation

| Script | Description |
|--------|-------------|
| `run_ai_tournament.py` | Run tournaments between submitted AI solutions |
| `evaluate_new_solution.py` | Evaluate a new solution against baselines |
| `verify_poker_score.py` | Verify poker scoring calculations |

## Debugging

| Script | Description |
|--------|-------------|
| `debug_poker_match.py` | Debug individual poker matches |

## Usage

Run from the repository root:

```bash
python tools/debug_poker_match.py --help
python tools/run_ai_tournament.py
```

Or with module syntax:

```bash
python -m tools.debug_poker_match
```
