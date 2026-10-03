# Selection transfer replication: interpretation

The registered primary comparison is inconclusive. Food-trained controllers
minus neutral descendants on held-out ball scenarios have mean −0.0072373 and
a seed-bootstrap 95% interval [−0.0174965, +0.0024784]. The registered positive
threshold requires the lower bound to exceed +0.01. Seven of twelve independent
outer seeds have positive differences; this does not satisfy the rule.

Transfer versus the default controller is negative: mean −0.0127234, interval
[−0.0199838, −0.0057617]. Food performance improves versus founders (mean
+0.0213218, interval [+0.0135395, +0.0290617]), but this founder comparison
does not isolate selection from neutral evolution. The useful memory mechanism
and founder improvements do not establish beneficial cross-domain selection.

The full [JSON](selection_replication.json) retains all seed rows, controls,
scenario identities, trajectory/genome summaries and start-of-run provenance.
The [Markdown](selection_replication.md) is generated from that JSON. The
[original preregistration](selection_transfer_preregistration.md) remains
unchanged. A separate [presentation clarification](selection_presentation_clarification.md)
aligns the headline with the already registered neutral contrast and practical
threshold; it does not change the contrast, seeds, budget or decision rule.
Historical v4 artifacts lack provenance, so differing values cannot establish
a before/after code improvement.

The controls share founders, population, generations and mutation operators.
They do not have identical evaluator-call budgets: selected arms choose validation
elites while neutral evolution returns a shuffled final-generation descendant.
The result therefore cannot isolate the contribution of validation selection.
Published v4 scenarios are development evidence, not independent confirmation.
Adaptation reference scores were established on only two seeds; no acceleration
claim is supported.

Stop substrate expansion. A bounded next diagnostic could test whether shorter
food-selected memory contributes to the deficit on decelerating ball scenarios,
using controlled parameter intervention and a separately frozen decision rule.
The observed parameter drift and family scores motivate that hypothesis, but
do not prove it. No behavior algorithm, champion or poker binding changes are
part of this replication.

Reproduction from the repository root (PowerShell):

```powershell
.\.venv\Scripts\python.exe scripts/run_target_memory_transfer_study.py --seeds 0,1,2,3,4,5,6,7,8,9,42,123 -j 3 --output research/target_memory_transfer/selection_replication.json
.\.venv\Scripts\python.exe tools/check_transfer_report.py research/target_memory_transfer/selection_replication.json
```

Budget: 32 individuals × 30 generations × 5 search runs per selected arm;
16 training, 8 validation and 16 held-out scenarios; 10,000 seed-bootstrap
resamples with bootstrap seed 1234. The completed run took 1968.8 seconds.
The artifact records the starting revision, working-diff hash, source hashes,
configuration/scenario identities, interpreter/platform and preregistration hash.
The revision names the starting checkout, including explicitly recorded local
changes, rather than claiming the experiment ran from the later PR commit.
