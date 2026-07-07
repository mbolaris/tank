# Tank World Federation

> **Status**: Proposal (July 2026). Foundational, pre-implementation. This document
> describes the target design for connecting independent tanks into a shared,
> online ecosystem where fish migrate between players. It expands
> [VISION.md](VISION.md) Phase 5 (Distributed Compute) and the "Multi-tank network"
> line in [ROADMAP.md](ROADMAP.md).

---

## The Goal

Anyone can run a tank on their own machine, watch their fish evolve, and — when they
choose to — connect it to a network where fish migrate to and from other people's
tanks. Your lineage competes, breeds, and spreads across the ecosystem. The moment a
player can say *"my fish's descendant just won a poker tournament in someone else's
tank,"* Tank World has a viral loop that no single-machine simulation can produce.

Federation is what turns Tank World from a research framework into a **living,
shared digital ecosystem**. It is also the highest-risk surface we will ever build,
because it means accepting data — and, done naively, code — from strangers. The three
non-negotiable design commitments below exist to make federation safe *and* fun at
the same time.

---

## Commitment 1: Genomes Are Data, Never Code

**A fish that arrives from another tank must be a versioned data record, never an
executable payload.** This is the single most important rule in the entire
federation design. If foreign fish could ship code, the network would be a
remote-code-execution botnet wearing an aquarium costume.

Tank World is unusually well positioned to honor this rule because the composable
behavior system already represents a fish's brain as pure data:

- Four categorical choices — `threat_response`, `food_approach`, `social_mode`,
  `poker_engagement` (see `core/algorithms/composable/definitions.py`)
- A flat `parameters: dict[str, float]` of tuned continuous values
- Genetic traits (`core/genetics/`) that are likewise numeric/categorical

A migrating fish is therefore fully described by a handful of enum names plus a
bounded dictionary of floats. That is trivially serializable, trivially validated,
and trivially sandboxed — because there is nothing to execute.

### The `GenomeCodePool` Boundary

`GenomeCodePool` (see `docs/architecture/python_code_pool.md`) allows *locally
authored* Python movement policies. **The code pool must never cross the federation
boundary.** A fish that relies on a code-pool policy either migrates with that policy
stripped (falling back to composable behavior), or is not eligible for migration at
all. The wire format has no field for source code, and the importer must reject any
payload that attempts to smuggle one.

This gives us a clean split:

| Path | Behavior representation | Trust model |
|------|------------------------|-------------|
| Local tank | Composable behavior **or** code-pool policy | Full trust (you wrote it) |
| Federated migration | Composable behavior + traits **only** | Zero trust (data-only, validated) |

---

## Commitment 2: A Versioned Wire Format, Specified Before Launch

The most expensive mistake we can make is letting two incompatible tanks exist in the
wild before the migration format is specified. **We define the wire schema — with a
version field — now, while there is exactly one implementation.**

### `MigratingFish` schema (v1 draft)

```jsonc
{
  "wire_version": 1,               // integer; importer rejects unknown majors
  "genome": {
    "behavior": {
      "threat_response": "PANIC_FLEE",
      "food_approach":   "DIRECT_PURSUIT",
      "social_mode":     "SOLO",
      "poker_engagement":"PASSIVE",
      "parameters": { "flee_distance": 42.0, "pursuit_aggression": 0.7 }
    },
    "traits": { "size": 0.6, "metabolism": 1.1, "color_hue": 210 },
    "lineage_id": "sha256:...",     // stable ancestry hash (see below)
    "generation": 37
  },
  "provenance": {
    "origin_tank": "opaque-tank-id",
    "exported_at": 1782240000,
    "schema_source": "tankworld/0.2.0"
  }
}
```

### Import validation is mandatory and total

Every field is checked before a foreign fish is instantiated:

- `wire_version` major must be recognized; unknown → reject.
- Every enum name must resolve in the *local* registry. Unknown enum → reject
  (never silently coerce — that corrupts lineage semantics).
- Every parameter key must be a known parameter; every value must be finite and
  clamped to the parameter's declared bounds (`SUB_BEHAVIOR_PARAMS`).
- Traits validated against `core/genetics/` bounds and sanitizers (the existing
  `test_genome_sanitization`, `test_genome_validation` suites extend to cover the
  wire path).
- Any extra/unexpected key → reject (strict schema, no passthrough).

We already have `core/transfer/entity_transfer.py`, migration protocol tests, and
`test_genome_compatibility` as a head start. Federation formalizes that internal
transfer format into a **public, versioned, adversarially-validated** one.

### Compatibility policy

- **Strict per supported schema.** A v1 importer accepts exactly the v1 shape above;
  unexpected fields are rejected rather than ignored.
- **New wire shapes require negotiated support.** If we need additional fields, tanks
  advertise supported schema versions during handshake before either side sends them.
- **Breaking changes bump the major** and are gated by a compatibility window.
- A conformance suite (`tests/test_federation_wire_conformance.py`, planned) pins the
  v1 schema with golden fixtures, the same way `test_replay_golden` pins replays.

---

## Commitment 3: Separate the Deterministic Path From the Social Path

Determinism is Tank World's research crown jewel (see
[VISION.md](VISION.md) → "Determinism is Non-Negotiable"). Federation is inherently
non-deterministic — fish arrive whenever the network delivers them. Rather than
compromise either property, we make the boundary explicit with **two run modes**:

| Mode | Used for | Determinism | Migration |
|------|----------|-------------|-----------|
| **Sealed** | Benchmarks, champions, CI, research | Byte-for-byte reproducible from seed | Disabled |
| **Open** | Online/federated play | Not seed-reproducible | Enabled, event-logged |

The rules that keep them from contaminating each other:

1. **Benchmarks and champion verification always run in Sealed mode.** No champion is
   ever recorded from an Open-mode run. This protects the entire Layer 1 evolution
   loop from network noise.
2. **Open mode logs every migration as a replayable event.** A tank in Open mode is
   not reproducible from a seed alone, but it *is* reproducible from
   `seed + ordered migration event log`. This reuses the existing replay
   infrastructure (see [REPLAY.md](REPLAY.md)) so "watch exactly how this foreign
   fish arrived and took over" becomes both a debugging tool and a spectator feature.
3. **Mode is a first-class, test-enforced flag**, not a runtime guess — mirroring how
   phase order and import boundaries are enforced by tests today.

---

## Lineage and Ancestry as a Feature

Federation makes ancestry the emotional core of the product, so lineage must be
first-class data:

- **Stable `lineage_id`**: a content hash of the founding genome plus an ordered
  ancestry chain, so a fish's descendants remain traceable across tank boundaries.
- **Cross-tank phylogeny**: because git is already the heredity mechanism for *code*,
  we mirror the idea for *fish* — every migration is an edge in a distributed
  family tree that any tank can render.
- **Hall of Fame**: the champions registry (`champions/`) gains an optional
  federated view — notable lineages, longest-surviving bloodlines, tournament
  winners — feeding the story layer described in [ROADMAP.md](ROADMAP.md).

See [MINIGAME_PLUGINS.md](MINIGAME_PLUGINS.md) for how poker/soccer results become
shareable lineage highlights.

---

## Security Threat Model (Summary)

| Threat | Mitigation |
|--------|-----------|
| Remote code execution via migrated fish | Data-only wire format; no code field; code pool never crosses boundary |
| Malformed/adversarial payloads | Total strict-schema validation; clamp to bounds; reject unknown keys |
| Resource exhaustion (migration flooding) | Rate-limit inbound migrations; bounded import queue |
| Lineage tampering / spoofed provenance | Provenance is advisory; `lineage_id` gives a canonical, tamper-evident identity for the ancestry data. Authentic origin claims require a future signature/attestation layer |
| Version skew between tanks | Schema-version negotiation; strict conformance fixtures |
| Determinism contamination of research | Sealed vs Open mode split; champions only from Sealed runs |

Federation deliberately assumes **zero trust** in the sending tank. Nothing a peer
says about a fish is trusted except the parts we can independently validate or
recompute.

---

## Phased Delivery

Sequenced so the hard-to-change foundations land before anything is exposed to the
network:

1. **Wire format v1 + conformance fixtures** (do this first, before two tanks exist).
2. **Export/import round-trip in Sealed mode** — prove a fish survives serialize →
   validate → reconstruct with identical behavior, reusing `entity_transfer.py`.
3. **Open mode + migration event log** built on the replay system.
4. **Local peer sync** (two tanks on a LAN / one host) — the smallest real network.
5. **Hosted relay + lineage service** — the "run a tank, see it join the ocean"
   experience.
6. **Federated Hall of Fame + story layer** — the viral loop.

---

## Relationship to Existing Docs

- [VISION.md](VISION.md) — Phase 5 Distributed Compute (this doc is its design).
- [ROADMAP.md](ROADMAP.md) — "Multi-tank network with data-only fish/genome migration".
- [REPLAY.md](REPLAY.md) — the record/replay substrate Open mode builds on.
- [MINIGAME_PLUGINS.md](MINIGAME_PLUGINS.md) — the entertainment layer whose results
  become shareable across the federation.
- `core/transfer/entity_transfer.py` — the internal transfer code this formalizes.

---

*Last updated: July 2026*
