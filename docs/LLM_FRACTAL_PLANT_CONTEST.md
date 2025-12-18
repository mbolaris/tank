# LLM Fractal Plant Beauty Contest

## Overview

The Fish Tank features a unique "beauty contest" where different LLM-themed fractal plants compete for survival and visual dominance. Each plant variant represents a different AI model's aesthetic philosophy, rendered using various fractal techniques.

## Contest Objectives

1. **Visual Excellence**: Create the most beautiful, distinctive plant that stands out in the ecosystem.
2. **Botanical Authenticity**: Leaves, stems, roots, and buds should read as plant tissue—avoid "clouds of pixels" that have no trunk.
3. **Survival Fitness**: Thrive through energy collection, nectar production, and poker battles; beauty should emerge from growth, not static screenshots.
4. **Unique Identity**: Each LLM variant must own a palette, branching rhythm, and motion style no other model uses.
5. **Readable Silhouette**: Even when zoomed out, the outline should communicate plant structure (fern fronds, banyan canopy, rosette base, etc.).
6. **Self-Justifying Rules**: Production rules should explain visible features (e.g., bracket-heavy rules for aerial roots, alternating turns for leaf rosettes).

## How the Contest Works

### Balanced Representation
The simulation ensures all LLM variants get fair representation:
- Initial spawn distributes variants evenly across root spots
- Reproduction prefers underrepresented variants
- No single variant can dominate the ecosystem

### Fitness Metrics
Plants earn fitness points through:
- **Energy Collection**: Passive growth from photosynthesis (time-of-day dependent)
- **Survival Duration**: Longevity in the tank
- **Nectar Production**: Successfully creating collectible nectar (30 points each)
- **Poker Victories**: Winning poker games against fish (20 points each)

### Reproduction Cycle
1. Plants accumulate energy through passive growth
2. When energy exceeds threshold, nectar is produced
3. Fish consuming nectar trigger plant reproduction
4. Offspring inherit parent genome with mutations

---

## LLM Variants

### Sonnet 4.5 (NEW - The Botanical Champion)
**Philosophy**: Elegant, organic beauty through proper L-system botany

| Attribute | Value |
|-----------|-------|
| **Fractal Type** | L-System (Fern Pattern) |
| **Color Palette** | Coral/Terracotta (hue: 0.02-0.08) |
| **Visual Style** | Natural fern fronds with organic branching |
| **L-System Rules** | `X -> F+[[X]-X]-F[-FX]+X` (classic fern) |
| **Special Features** | Elegant curved leaves, natural asymmetry, subtle ambient glow |
| **Poker Style** | Balanced (moderate aggression, thoughtful bluffing) |

**Design Rationale**: Unlike other variants that use abstract mathematical fractals (Mandelbrot, Julia, etc.), Sonnet 4.5 uses proper botanical L-system rules that produce actual plant-like structures. The warm coral/terracotta palette distinguishes it from the green base plants while maintaining organic aesthetics.

**L-System Production Rules**:
```
X -> F+[[X]-X]-F[-FX]+X  (55% - primary fern frond)
X -> F-[[X]+X]+F[+FX]-X  (35% - secondary upright growth)
X -> FX                   (10% - simple elongation)
F -> FF                   (100% - stem extension)
```

---

### GPT-5.1 Codex (NEW - Recursive Banyan Scribe)
**Philosophy**: A banyan grove that writes its own code—layered canopies stitched together by aerial roots and subtle syntax glyphs.

| Attribute | Value |
|-----------|-------|
| **Fractal Type** | Stochastic L-System (aerial root recursion) |
| **Color Palette** | Cool jade trunks (hue: 0.30–0.40) with neon ink highlights (0.55–0.60) |
| **Visual Style** | Tiered canopies with looping roots that reconnect to the soil and trunk | 
| **Special Features** | Woven bark striations hinting at brackets/semicolons, oscillating leaf fans, nectar nodes pulsing like cursor blinks |
| **Poker Style** | Patient setup with sharp counter-bluffs |

**Design Rationale**: To stay plant-first, Codex leans on banyan cues: downward roots, wide crown plates, and repeating buttress arcs. The jade-and-ink palette separates it from the Sonnet warm tones and GPT cyan mesh while the bracket-like bark ties back to "coding" DNA without losing botanical readability.

**L-System Production Rules**:
```
Axiom: X
X -> F[+X][-X]R[&FX]        (40% - build mirrored canopy lobes plus an aerial root)
X -> F[+R][-R]X             (30% - root-first growth that loops into the next layer)
X -> FF[+FX][-FX]           (20% - elongation with small leaf fans)
R -> F[&F]f                 (10% - aerial root that drapes downward before budding)
F -> FF                     (100% - trunk/branch extension)
```

**Implementation Checklist** (so judges know the Recursive Banyan spec is honored):
- Spawn using the above axiom/rules with `angle` noise ±3° to vary canopy fans without breaking symmetry.
- Render bark striations with alternating 1px/2px lines to evoke `;`/`}` motifs while keeping trunks matte jade.
- Give aerial roots slightly darker saturation than branches so they read as separate organs when they reattach to soil.
- Keep nectar pulses localized to branch junctions (never whole-branch glows) to preserve the banyan silhouette.

**Rendering Notes**:
- Draw bark striations as alternating thin/dense strokes to mimic `;` and `}` shapes without literal text overlays.
- Vary downward bend (`&`) noise slightly so roots arc naturally toward the substrate before curving back up.
- Pulse nectar nodes at branch junctions with a brief neon accent to suggest a "cursor" heartbeat.

---

### Claude (Golden Spiral)
**Philosophy**: Mathematical elegance through Julia sets and Fibonacci aesthetics

| Attribute | Value |
|-----------|-------|
| **Fractal Type** | Julia Set |
| **Color Palette** | Golden/Amber (hue: 0.08-0.14) |
| **Visual Style** | 5-petal Fibonacci flower with spiral animation |
| **Special Features** | Golden ratio proportions, sparkle particles, pulsing bloom |
| **Poker Style** | Balanced with moderate bluffing |

---

### GPT (Neural Network)
**Philosophy**: Interconnected complexity inspired by neural architectures

| Attribute | Value |
|-----------|-------|
| **Fractal Type** | Tricorn |
| **Color Palette** | Electric Cyan/Teal (hue: 0.48-0.55) |
| **Visual Style** | Hexagonal network nodes with electric connections |
| **Special Features** | Neural connection lines, electric sparks, node points |
| **Poker Style** | Aggressive with high bluff frequency |

---

### Mandelbrot (Mathematical Beauty)
**Philosophy**: Pure mathematical fractal aesthetics

| Attribute | Value |
|-----------|-------|
| **Fractal Type** | Mandelbrot Set |
| **Color Palette** | Deep Purple (hue: 0.55-0.75) |
| **Visual Style** | Wavy leaf outline with vein impressions |
| **Special Features** | Smooth iteration coloring, botanical glow aura |
| **Poker Style** | Conservative with low bluffing |

---

### Antigravity (Ethereal Vortex)
**Philosophy**: Defying natural order with inverted growth patterns

| Attribute | Value |
|-----------|-------|
| **Fractal Type** | Burning Ship |
| **Color Palette** | Violet (hue: 0.70-0.85) |
| **Visual Style** | Asymmetric flame patterns with swirling vortex |
| **Special Features** | Rising floating particles, ethereal glow, diamond leaves |
| **Poker Style** | Most aggressive with highest risk tolerance |

---

### L-System (Traditional Botanical)
**Philosophy**: Classic procedural plant generation

| Attribute | Value |
|-----------|-------|
| **Fractal Type** | Traditional L-System |
| **Color Palette** | Green (hue: 0.25-0.45) |
| **Visual Style** | Standard botanical branching with leaves |
| **Special Features** | Dynamic branching, elliptical leaves with veins |
| **Poker Style** | Variable (randomized traits) |

---

## LLM Playbooks for Plant-First Competition

- **Claude (Golden Spiral)**: Borrow sunflower phyllotaxis for leaf placement, add Fibonacci-inspired petal clusters at branch tips, and animate bloom pulses that travel along spiral arms.
- **GPT (Neural Network)**: Turn node graphs into leaf whorls joined by vein conduits; let electrical sparks stay inside midribs so the silhouette remains tree-like instead of nebulous.
- **Antigravity (Ethereal Vortex)**: Counterweight the inverted swirl with a visible root crown and dangling seed pods; constrain vortex trails to leaf edges so the plant still reads as foliage.
- **Mandelbrot (Mathematical Beauty)**: Soften jagged boundaries into lobed leaves, then fade iteration colors into vein gradients; treat minibrots as budding calyxes rather than raw set outlines.
- **Sonnet 4.5 (Botanical Champion)**: Keep the L-system stochastic but limit deviation so fronds overlap naturally; slight leaf tip noise prevents the "perfect clone" look.
- **Gemini 3Pro (Cosmic Multimodal)**: Place nebula glows at node junctions, not across entire branches; punctuate with tiny star blossoms that twinkle on a beat synced to nectar readiness.
- **GPT-5.1 Codex (Recursive Banyan)**: Alternate canopy fans and descending roots; carve subtle bracket/semicolon striations into bark while keeping leaves broad and matte so the syntax motif never overwhelms plant texture.

These playbooks ensure every LLM remains legibly botanical while expressing a unique identity that the judges can immediately recognize.

---

## How to Add a New LLM Variant

### Step 1: Backend (Python)

**File**: `core/genetics/plant.py`

Add a new factory method to `PlantGenome`:

```python
@classmethod
def create_your_variant(cls, rng: Optional[random.Random] = None) -> "PlantGenome":
    """Create a YourLLM plant - description of aesthetic."""
    rng = rng or random
    g = cls(
        axiom="X",  # or "F" for simpler patterns
        angle=rng.uniform(20.0, 30.0),  # Branching angle in degrees
        length_ratio=rng.uniform(0.65, 0.75),  # Segment reduction ratio
        branch_probability=rng.uniform(0.8, 0.95),
        curve_factor=rng.uniform(0.1, 0.2),
        color_hue=rng.uniform(X, Y),  # YOUR UNIQUE HUE RANGE
        color_saturation=rng.uniform(0.7, 0.9),
        stem_thickness=rng.uniform(0.8, 1.2),
        leaf_density=rng.uniform(0.6, 0.9),
        # Poker traits
        aggression=rng.uniform(0.3, 0.6),
        bluff_frequency=rng.uniform(0.1, 0.3),
        risk_tolerance=rng.uniform(0.3, 0.6),
        # Energy traits
        base_energy_rate=rng.uniform(0.02, 0.045),
        growth_efficiency=rng.uniform(1.0, 1.4),
        nectar_threshold_ratio=rng.uniform(0.6, 0.8),
        fractal_type="your_variant",
    )
    # Define L-system production rules
    g._production_rules = [
        ("X", "your_pattern_here", probability),
        ("F", "FF", 1.0),  # Standard stem extension
    ]
    return g
```

**Add color mutation range** in `from_parent()`:
```python
elif parent.fractal_type == "your_variant":
    color_min, color_max = X, Y  # Your hue range
```

### Step 2: Register Variant

**File**: `core/simulation_engine.py`

Add to `_fractal_variants` list:
```python
self._fractal_variants = [
    "mandelbrot",
    "claude",
    "antigravity",
    "gpt",
    "sonnet",
    "your_variant",  # Add here
    "lsystem",
]
```

Add to `_create_variant_genome()`:
```python
variant_factories = {
    ...
    "your_variant": PlantGenome.create_your_variant,
    ...
}
```

### Step 3: Frontend (TypeScript)

**File**: `frontend/src/utils/fractalPlant.ts`

1. Update the type union:
```typescript
fractal_type?: 'lsystem' | 'mandelbrot' | 'claude' | 'antigravity' | 'gpt' | 'sonnet' | 'your_variant';
```

2. Add cache (if using custom textures):
```typescript
const yourVariantCache = new Map<number, YourCacheType>();
```

3. Add dispatch in `renderFractalPlant()`:
```typescript
if (fractalType === 'your_variant') {
    renderYourVariantPlant(ctx, plantId, genome, x, y, sizeMultiplier, iterations, elapsedTime, nectarReady);
    return;
}
```

4. Implement rendering function - either:
   - Use L-system rendering (like Sonnet) for plant-like structures
   - Generate custom fractal texture (like Mandelbrot, Claude, GPT)

---

## Design Guidelines for New Variants

### DO:
- Choose a distinctive color palette that doesn't overlap with existing variants
- Create recognizable visual signatures
- Consider using botanical L-system rules for plant-like appearance
- Add subtle animations (sway, glow, particles) for life

### DON'T:
- Use colors too similar to existing variants
- Create purely abstract patterns with no organic feel
- Forget to add the variant to all required files
- Skip the mutation color range (breaks offspring coloring)

### L-System Tips for Plant-Like Appearance

Classic botanical patterns:
```
# Fern frond
X -> F+[[X]-X]-F[-FX]+X

# Bush
F -> FF+[+F-F-F]-[-F+F+F]

# Binary tree
F -> F[-F]F[+F]F

# Weed/grass
F -> FF-[-F+F+F]+[+F-F-F]
```

The `[` and `]` brackets control branching (push/pop turtle state).
`+` and `-` control turning left/right by the angle parameter.
`F` draws forward, `X` is typically used as a variable that expands but doesn't draw.

---

## Competition Tracking

The simulation automatically tracks:
- Population count per variant
- Fitness scores (energy, survival, reproduction, poker wins)
- Variant representation balance

The system ensures fair competition by preferring underrepresented variants during reproduction, preventing any single LLM from dominating the tank.

---

## The Challenge

Can your LLM create a fractal plant that:
1. Looks like a real plant (not abstract math)?
2. Has a unique, recognizable aesthetic?
3. Survives and thrives in the ecosystem?
4. Wins the beauty contest through visual excellence?

May the best plant win!
