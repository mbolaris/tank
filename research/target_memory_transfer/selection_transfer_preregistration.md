# Selection-specific transfer replication protocol

Registered 2026-10-03 before the new replication output is produced. This is
a diagnostic replication, not an independent confirmation or a promotion run.
Published v4 scenarios are development evidence. No graph operators, controller
parameters, or champion records change in this work.

The single primary contrast is **food-trained minus matched neutral evolution
on held-out ball fitness**, averaged within outer seed. Practical improvement
requires the lower bound of its 95% deterministic bootstrap interval to exceed
**0.01 fitness units**. A CI wholly below zero is negative; every other outcome
is inconclusive for useful transfer. Do not replace this contrast after observing
results. Always publish transfer versus default and founders as secondary effects.

Use exactly seeds `0,1,2,3,4,5,6,7,8,9,42,123`, population 32, generations 30,
five evolution runs per arm, 16 food/ball training scenarios, eight validation
scenarios per domain, and 16 held-out ball scenarios. One independent analysis
unit is an outer seed; five inner runs and individual episodes are not independent
replicates. Use the existing 10,000-resample bootstrap with RNG seed 1234.
No optional stopping, discarded seeds, reruns to select a favorable outcome, or
post-hoc scenario-family filtering. Cap the campaign at these 12 seeds and this
budget; worker failure invalidates publication until all planned seeds complete.

Reproduce all existing arms: food-trained, ball-trained, neutral, founders,
default, and naive greedy. The three evolving arms share founder populations,
parameter encoding, mutation/crossover operators, population size and generation
budget. Existing neutral evolution shuffles fitness and returns a final-generation
descendant; selected arms choose their elite with validation. Thus validation
selection is part of the treatment, and exact evaluation counts differ. This
replication cannot isolate that component of selection. Do not silently modify
the neutral control to make a stronger claim.

Freeze the current generator and its train/validation/food-held-out/ball-held-out
salts. Record content hashes of evaluator/source files, complete configuration,
scenario-generator identity, interpreter/platform, git revision and working diff
identity in the output. Historical artifacts without these fields remain unknown.
The source-learning diagnostic is food-trained minus founders on food-held-out
fitness; require its lower 95% bound above zero before continuing transfer work.
If absent, stop the campaign and version a separate diagnostic change. If source
learning is present but transfer is negative/inconclusive, publish that result;
one bounded mechanism hypothesis must precede substrate expansion.

Independent confirmation is a subsequent preregistration using new outer seeds
and a separately versioned scenario set, frozen before any target scores are
seen. This run grants no promotion permission; that also requires the repository's
multi-seed ecosystem checks. Live population history is stored in world saves,
never appended to benchmark `research/skill_history.jsonl`.

Reproduction (from the repository root, using its virtual environment):

```powershell
.\.venv\Scripts\python.exe scripts/run_target_memory_transfer_study.py --seeds 0,1,2,3,4,5,6,7,8,9,42,123 -j 3 --output research/target_memory_transfer/selection_replication.json
```

The output's original overall headline remains the existing transfer-vs-default
decision rule for continuity. `selection_decision` records this protocol's primary
verdict separately and names its contrast explicitly.
