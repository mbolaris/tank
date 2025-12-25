# Adding Gene Distribution Graphs

This guide explains how to add a new gene trait distribution graph to the Gene Distribution panel. Follow this checklist to ensure all required changes are made.

## Required Files Checklist

When adding a new gene trait (e.g., `tail_size`), you must modify these files **in order**:

### 1. Backend: Generate Stats
**File:** `core/simulation_engine.py` - `get_stats()` method

Add histogram generation logic:
```python
# Tail size stats
try:
    tail_sizes = [getattr(f.genome, 'tail_size', 1.0) for f in fish_list] if fish_list else []
    if tail_sizes:
        stats["tail_size_min"] = min(tail_sizes)
        stats["tail_size_max"] = max(tail_sizes)
        stats["tail_size_median"] = sorted(tail_sizes)[len(tail_sizes) // 2]
        # Histogram bins
        bins = 10
        bin_min, bin_max = 0.5, 2.0  # Use allowed range for this trait
        bin_width = (bin_max - bin_min) / bins
        edges = [bin_min + i * bin_width for i in range(bins + 1)]
        counts = [0] * bins
        for size in tail_sizes:
            idx = int((size - bin_min) / bin_width)
            if idx < 0:
                idx = 0
            elif idx >= bins:
                idx = bins - 1
            counts[idx] += 1
        stats["tail_size_bins"] = counts
        stats["tail_size_bin_edges"] = edges
    else:
        stats["tail_size_min"] = 0.0
        stats["tail_size_max"] = 0.0
        stats["tail_size_median"] = 0.0
        stats["tail_size_bins"] = []
        stats["tail_size_bin_edges"] = []
except Exception:
    stats["tail_size_min"] = 0.0
    stats["tail_size_max"] = 0.0
    stats["tail_size_median"] = 0.0
    stats["tail_size_bins"] = []
    stats["tail_size_bin_edges"] = []

# Expose allowed range constants
stats["allowed_tail_size_min"] = 0.5
stats["allowed_tail_size_max"] = 2.0
```

### 2. Backend: Define Data Structure
**File:** `backend/state_payloads.py` - `StatsPayload` dataclass

Add fields to the dataclass:
```python
# Tail size statistics
tail_size_min: float = 0.0
tail_size_max: float = 0.0
tail_size_median: float = 0.0
tail_size_bins: List[int] = field(default_factory=list)
tail_size_bin_edges: List[float] = field(default_factory=list)
allowed_tail_size_min: float = 0.0
allowed_tail_size_max: float = 0.0
```

Also add to the `to_dict()` method:
```python
# Tail size fields
"tail_size_min": self.tail_size_min,
"tail_size_max": self.tail_size_max,
"tail_size_median": self.tail_size_median,
"tail_size_bins": self.tail_size_bins,
"tail_size_bin_edges": self.tail_size_bin_edges,
"allowed_tail_size_min": self.allowed_tail_size_min,
"allowed_tail_size_max": self.allowed_tail_size_max,
```

### 3. Backend: Pass Data Through
**File:** `backend/simulation_runner.py` - `_collect_stats()` method

Add the fields to the `StatsPayload` constructor call:
```python
# Tail size fields
tail_size_min=stats.get("tail_size_min", 0.0),
tail_size_max=stats.get("tail_size_max", 0.0),
tail_size_median=stats.get("tail_size_median", 0.0),
tail_size_bins=stats.get("tail_size_bins", []),
tail_size_bin_edges=stats.get("tail_size_bin_edges", []),
allowed_tail_size_min=stats.get("allowed_tail_size_min", 0.5),
allowed_tail_size_max=stats.get("allowed_tail_size_max", 2.0),
```

### 4. Frontend: TypeScript Types
**File:** `frontend/src/types/simulation.ts` - `SimulationStats` interface

Add type definitions:
```typescript
// Tail size statistics
tail_size_min?: number;
tail_size_max?: number;
tail_size_median?: number;
tail_size_bins?: number[];
tail_size_bin_edges?: number[];
allowed_tail_size_min?: number;
allowed_tail_size_max?: number;
```

### 5. Frontend: Render Graph
**File:** `frontend/src/components/EcosystemStats.tsx`

Add the `SizeSummaryGraph` component in the Gene Distribution section:
```tsx
<SizeSummaryGraph
    bins={safeStats.tail_size_bins || []}
    binEdges={safeStats.tail_size_bin_edges || []}
    min={safeStats.tail_size_min}
    median={safeStats.tail_size_median}
    max={safeStats.tail_size_max}
    allowedMin={safeStats.allowed_tail_size_min ?? 0.5}
    allowedMax={safeStats.allowed_tail_size_max ?? 2.0}
    width={280}
    height={100}
    xLabel="Tail Size"
    yLabel="Count"
/>
```

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         DATA FLOW PIPELINE                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  1. GENERATION                                                           │
│     core/simulation_engine.py::get_stats()                              │
│     - Calculates min/max/median from fish genomes                       │
│     - Creates histogram bins and edges                                  │
│     - Returns stats dict                                                │
│                          ↓                                              │
│  2. DATA STRUCTURE                                                       │
│     backend/state_payloads.py::StatsPayload                             │
│     - Defines dataclass fields with types                               │
│     - Includes to_dict() serialization                                  │
│                          ↓                                              │
│  3. STATE COLLECTION                                                     │
│     backend/simulation_runner.py::_collect_stats()                      │
│     - Extracts stats from engine                                        │
│     - Creates StatsPayload instance  ← ⚠️ OFTEN MISSED!                │
│     - Sends via WebSocket                                               │
│                          ↓                                              │
│  4. FRONTEND TYPES                                                       │
│     frontend/src/types/simulation.ts::SimulationStats                   │
│     - TypeScript interface for type safety                              │
│                          ↓                                              │
│  5. RENDERING                                                            │
│     frontend/src/components/EcosystemStats.tsx                          │
│     - Uses SizeSummaryGraph component                                   │
│     - Displays histogram in Gene Distribution panel                     │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## Common Mistakes

1. **Missing `simulation_runner.py` passthrough** - Data is generated but not included in the StatsPayload constructor call
2. **Missing `to_dict()` entry** - Fields defined in dataclass but not serialized
3. **Mismatched field names** - Typo in field name across files
4. **Wrong default values** - Using `0.0` for allowed_min when it should be `0.5`

## Testing

After adding a new graph:
1. Start the simulation with at least a few fish
2. Open the Gene Distribution panel
3. Verify all graphs display data (no blank graphs)
4. Check browser console for any TypeScript errors
