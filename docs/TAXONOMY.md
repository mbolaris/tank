# Taxonomy and Species Naming

Tank World's taxonomy system gives each fish and petri-world microbe a stable,
human-readable identity derived from its heritable traits. It is an
observational layer: it labels evolutionary history, but never changes genome
selection, reproduction, energy, or behaviour.

## What an entity carries

An organism may expose the following metadata:

- `taxon_id` — the registry identifier (`prov_*` while provisional, then
  `taxon_*` when established);
- `common_name` and `scientific_name` — deterministic names derived from its
  founding type profile;
- `species_confidence` — `provisional`, `established`, or `extinct` for a
  registry record; and
- `type_specimen_id` — the founding organism used as the taxonomic reference.

Microbes additionally expose a `strain_id`. The backend includes this metadata
in entity-detail and world snapshot payloads, and the entity inspector renders
it when present.

## Classification lifecycle

1. At birth, `TaxonomySystem.register_birth()` builds an immutable,
   normalized `TaxonomyProfile` from the organism's taxonomically meaningful
   traits.
2. The registry compares that profile with the parent lineage and related,
   established taxa. Close descendants join an existing taxon; sufficiently
   distinct organisms begin a provisional lineage.
3. A provisional lineage becomes established only after meeting the registry's
   population, generation-persistence, and successful-birth thresholds. Its
   names are assigned at lineage creation and therefore do not change at
   establishment.
4. On every ecosystem update, the system reconciles restored or transferred
   organisms into the destination world's in-memory registry and evaluates
   provisional lineages. Death removes living membership.

The profile's type specimen is immutable. A taxon's current medoid may change
as its living membership changes, but that does not rename the taxon or rewrite
its founding evidence.

## Names and determinism

`core/taxonomy/naming.py` creates names from the type profile using stable
hashes. Common names use descriptive morphology and behaviour words; scientific
names use a generated genus and epithet. If an epithet would collide within a
genus, a deterministic qualifier is added. This keeps seeded runs reproducible
while avoiding accidental duplicate binomials in a registry.

Taxonomy metadata is deliberately excluded from replay fingerprints. It is
derived, observational state, so adding labels must not invalidate historical
deterministic replay fixtures.

## Persistence and transfers

Each ecosystem owns a `TaxonomySystem` and begins with a fresh in-memory
registry. `SpeciesRegistry.save()` and `load()` support explicit registry-file
persistence when a caller supplies a path; the normal ecosystem constructor
does not read a shared file, because that would let stale local state change a
seeded simulation. Transfers and restored entities retain their labels, and
the destination registry reconstructs the necessary membership without
counting a second birth.

## Extension points

- Add or adjust the traits used for distance classification in
  `core/taxonomy/profile.py`. Keep profiles normalized and immutable.
- Adjust membership and establishment thresholds in
  `core/taxonomy/registry.py`; benchmark any change because it affects the
  interpretation of evolutionary history.
- Extend naming vocabulary or naming rules in `core/taxonomy/naming.py` while
  preserving stable-hash determinism and collision handling.
- Wire a new organism type through `TaxonomySystem` with its own profile
  builder rather than reusing fish semantics.

## Verification

Run the focused suite with:

```powershell
py -3 -m pytest tests/test_taxonomy.py tests/test_entity_details_command.py tests/test_fingerprint_stream.py
```

For the repository's normal local validation, run:

```powershell
py -3 tools/agent_gate.py
py -3 tools/pre_pr_gate.py
```
