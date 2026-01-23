# Example Artifacts

This directory contains curated example artifacts for documentation purposes.

## What Belongs Here

- **Representative solution JSONs**: 1-2 examples showing the format of evolved fish strategies
- **Sample benchmark outputs**: Small examples of performance reports

## What Doesn't Belong Here

- **Generated output from scripts**: These should be gitignored
- **Large datasets**: Keep these in `data/` (also gitignored)
- **Live simulation logs**: Gitignored at repo root

## Generating Fresh Artifacts

Most generated artifacts go to `solutions/` (gitignored) or `logs/` (gitignored).

To capture a solution:
```bash
python scripts/submit_solution.py submit --file state.json --name "Example" --author "demo"
```

To generate a benchmark report:
```bash
python scripts/submit_solution.py report --print
```

## Files

- **ai_tournament_results.json**: Sample AI poker tournament results from Dec 2025. Shows tournament structure with Elo ratings, skill tiers, and head-to-head matchup data between different AI models.
