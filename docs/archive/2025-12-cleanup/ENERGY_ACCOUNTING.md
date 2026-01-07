# Energy accounting

This project tracks **fish** and **plant** energy changes with explicit, windowed ledgers so we can:

- Explain *where* energy is coming from / going to (UX + tuning).
- Reconcile “gains − losses” with the **true** change in population energy (anti-regression).

## Concepts

### Two separate economies

- **Fish energy economy** is recorded via `EcosystemManager.record_energy_gain/burn(...)`.
- **Plant energy economy** is recorded via `EcosystemManager.record_plant_energy_gain/burn(...)`.

Do not mix the two pools.

### “Recent window” stats

Windowed stats are computed over `ENERGY_STATS_WINDOW_FRAMES` (typically ~60s).

- Gains: `EcosystemManager.get_recent_energy_breakdown(...)`
- Burns: `EcosystemManager.get_recent_energy_burn(...)`
- True population delta: `EcosystemManager.get_energy_delta(...)`

The backend exposes reconciliation helpers:

- `energy_gains_recent_total`
- `energy_net_recent` (`gains − burns`)
- `energy_accounting_discrepancy` (`energy_net_recent − energy_delta.energy_delta`)

When `energy_accounting_discrepancy` is ~0, the windowed ledger matches the true fish-energy delta.

## How to record new energy changes

### Fish

- External inflow: call `ecosystem.record_energy_gain(source, amount)`
- External outflow: call `ecosystem.record_energy_burn(source, amount)`
- Signed deltas: use `ecosystem.record_energy_delta(source, delta)`
- Internal transfer (net 0): use `ecosystem.record_energy_transfer(source, amount)`

### Plants

Use the plant variants:

- `record_plant_energy_gain/burn/delta/transfer`

## Poker-specific rules

### Fish-vs-fish poker

Fish-vs-fish poker is an **internal transfer** plus a **house cut outflow**:

- `poker_fish`: total energy paid out to winners (after house cut)
- `poker_loss`: matching transfer volume so the internal transfer nets to 0 at the fish-population level
- `poker_house_cut`: true outflow from the fish population (should be > 0 when fish are playing)

### Mixed fish+plant poker

Mixed poker can remove energy via house cut, but **only the winner pays** it.

Policy implemented by `EcosystemManager.record_mixed_poker_outcome(...)`:

- If a **fish** wins: house cut appears only in fish economy (`poker_house_cut`).
- If a **plant** wins: house cut appears only in plant economy (`plant_energy_burn_recent.poker_house_cut`).

To keep reconciliation correct, the winner-side transfer is “grossed up” by the house cut when the cut is
surfaced as a separate burn.

## Regression tests

Energy accounting invariants live in `tests/test_energy_accounting.py`.

If you change any energy-modifying codepaths, add/adjust tests there to keep:

- reconciliation stable,
- house cut attribution correct,
- transfers net to zero when intended.
