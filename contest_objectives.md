# LLM Fractal Plant Beauty Contest

## Objectives
The goal of this contest is to determine which Large Language Model (LLM) can generate the most visually stunning, unique, and "plant-like" fractal organism.

## Competitors

### 1. Claude (The Golden Spiral)
- **Aesthetic**: Golden Julia set spirals with Fibonacci aesthetics.
- **Colors**: Amber, Gold, Warm Yellows.
- **Signature**: Mathematical perfection, recursive elegance.

### 2. GPT (The Neural Network)
- **Aesthetic**: Neural network-inspired branching patterns.
- **Colors**: Electric Cyan, Teal, Blue.
- **Signature**: High connectivity, dense branching, "electric" feel.

### 3. Antigravity (The Void Walker)
- **Aesthetic**: Inverted growth patterns that defy gravity.
- **Colors**: Violet, Deep Purple.
- **Signature**: Unconventional structure, upward/outward defiance.

### 4. Mandelbrot (The Classic)
- **Aesthetic**: Traditional Mandelbrot set structures.
- **Colors**: Deep Purple, Magenta.
- **Signature**: Infinite complexity, self-similarity.

### 5. Sonnet 4.5 (The Botanist)
- **Aesthetic**: Hyper-realistic fern and bush structures.
- **Colors**: Coral, Terracotta, Earthy Tones.
- **Signature**: Organic realism, natural asymmetry.

### 6. Gemini 3Pro (The Cosmic Multimodal)
- **Aesthetic**: "Deep Space" cosmic botanical.
- **Colors**: Deep Indigo, Violet, Starlight White.
- **Signature**: Complex, multimodal branching representing diverse data processing. High saturation, "galactic" feel.

## Judging Criteria
1.  **Plant-ness**: Does it look like a living organism?
2.  **Visual Impact**: Is the color palette and structure striking?
3.  **Uniqueness**: Does it stand out from standard L-systems?
4.  **Theme Adherence**: Does it represent its LLM namesake well?

## How to Enter (Implementation Guide)
To add a new LLM contestant to the beauty contest, follow these steps:

### 1. Define the Genome
In `core/plant_genetics.py`:
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
