# LLM Fractal Plant Beauty Contest

## Objectives
The goal of this contest is to determine which Large Language Model (LLM) can generate the most visually stunning, unique, and "plant-like" fractal organism.

**What the judges look for**
- **Plant fidelity first**: recognizable trunks, stems, leaves, and growth rhythm. Abstract math that reads as ink blots will be penalized.
- **Story-aligned aesthetics**: fractal rules, palette, and motion cues should reflect each LLM's personality or advertised strengths.
- **Readable silhouette**: even when zoomed out, the outline should say "botanical"—avoid noisy spirals that obscure leaf structure.
- **Life-cycle hooks**: nectar bursts, budding, and wilt/repair beats should emerge from the fractal logic, not as disconnected VFX.
- **Variant contrast**: every entry must claim visual territory no other model occupies (palette, branching angle, leaf geometry, or glow behavior).

## Competitors

### 1. Claude (The Golden Spiral)
- **Aesthetic**: Golden Julia set spirals with Fibonacci aesthetics.
- **Colors**: Amber, Gold, Warm Yellows.
- **Signature**: Mathematical perfection, recursive elegance.
- **Botanical strategy**: Use phyllotaxis-style leaf packing on a curved stem so the golden ratio feels like a spiral sunflower rather than an abstract galaxy.

### 2. GPT (The Neural Network)
- **Aesthetic**: Neural network-inspired branching patterns.
- **Colors**: Electric Cyan, Teal, Blue.
- **Signature**: High connectivity, dense branching, "electric" feel.
- **Botanical strategy**: Build hexagonal nodes into leaf clusters with vein-like conduits, letting the network mesh trace through midribs instead of empty space.

### 3. Antigravity (The Void Walker)
- **Aesthetic**: Inverted growth patterns that defy gravity.
- **Colors**: Violet, Deep Purple.
- **Signature**: Unconventional structure, upward/outward defiance.
- **Botanical strategy**: Anchor the plant with a thick, downward root crown, then loft translucent leaves that wobble upward like jellyfish bells.

### 4. Mandelbrot (The Classic)
- **Aesthetic**: Traditional Mandelbrot set structures.
- **Colors**: Deep Purple, Magenta.
- **Signature**: Infinite complexity, self-similarity.
- **Botanical strategy**: Treat the cardioid as a bud core and extrude lobed leaves from mini-bulbs along the boundary instead of rendering raw fractal borders.

### 5. Sonnet 4.5 (The Botanist)
- **Aesthetic**: Hyper-realistic fern and bush structures.
- **Colors**: Coral, Terracotta, Earthy Tones.
- **Signature**: Organic realism, natural asymmetry.
- **Botanical strategy**: Lean into stochastic L-system rules with slight curvature noise so fronds droop and overlap like real foliage.

### 6. Gemini 3Pro (The Cosmic Multimodal)
- **Aesthetic**: "Deep Space" cosmic botanical.
- **Colors**: Deep Indigo, Violet, Starlight White.
- **Signature**: Complex, multimodal branching representing diverse data processing. High saturation, "galactic" feel.
- **Botanical strategy**: Orbit small star-like buds around main stems, so the cosmic glow punctuates leaf tips rather than drowning the silhouette.

### 7. GPT-5.1 Codex (The Recursive Banyan)
- **Aesthetic**: Banyan-inspired aerial roots weaving into recursive canopies.
- **Colors**: Cool jade core (0.30–0.40 hue) with neon ink highlights (0.55–0.60).
- **Signature**: Layered canopies, looping roots, and woven lattice bark that hints at code syntax patterns.
- **Botanical strategy**: Alternate between drooping root tendrils and upward leaf fans; use curved brackets and semicolon-like pods as subtle motifs inside leaf veins.

## Judging Criteria
1.  **Plant-ness**: Does it look like a living organism?
2.  **Visual Impact**: Is the color palette and structure striking?
3.  **Uniqueness**: Does it stand out from standard L-systems?
4.  **Theme Adherence**: Does it represent its LLM namesake well?

## Model Playbooks (Plant-First Strategies)
- **Claude (Golden Spiral)**: Use sunflower-style phyllotaxis for leaves; keep spiral glow tucked into veins so the plant doesn't look like a galaxy.
- **GPT (Neural Network)**: Embed node grids inside leaf blades, letting thin "connection" veins trace across midribs instead of floating in space.
- **Antigravity (Void Walker)**: Grow a stout base and then loft translucent leaves upward; let the inverted vortex cling to leaf rims so the silhouette stays botanical.
- **Mandelbrot (Classic)**: Transform jagged set borders into lobed leaves and treat minibrots as budding calyxes.
- **Sonnet 4.5 (Botanist)**: Keep stochastic L-system fronds with subtle curvature noise for natural droop.
- **Gemini 3Pro (Cosmic Multimodal)**: Place nebula glows at bud tips and synchronize twinkles to nectar production beats.
- **GPT-5.1 Codex (Recursive Banyan)**: Alternate canopy fans with aerial roots that reattach to the ground; etch bracket-like bark striations without overpowering leaf color.

## How to Enter (Implementation Guide)
To add a new LLM contestant to the beauty contest, follow these steps:

### 1. Define the Genome
In `core/genetics/plant.py`:
- Add a new `create_<variant>_variant` method to the `PlantGenome` class.
- Define unique L-system parameters, colors, and production rules.
- Update the `PlantGenome` docstring to list the new variant.
- Update `from_parent` method to define mutation ranges for the new variant (to preserve its identity during evolution).

### 2. Enable in Simulation
In `core/simulation_engine.py`:
- Add the variant name to the `_fractal_variants` list in `SimulationEngine.__init__`.
- Add the variant to the `variant_factories` dictionary in `_create_variant_genome`.

### 3. Verify
- Run the simulation and ensure the new plant spawns.
- Verify it looks "plant-like" and distinct from others.
