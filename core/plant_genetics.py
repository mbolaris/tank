"""Genetics system for fractal plants.

This module provides a genetic system for evolving fractal plants with
heritable L-system parameters, poker skills, and energy traits.
"""

import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class PlantGenome:
    """Represents the genetic makeup of a fractal plant.

    Supports multiple LLM-themed fractal variants for the beauty contest:
    - lsystem: Traditional L-system fractals (green)
    - cosmic_fern: Complex fern structures (cosmic purple/violet)
    - claude: Golden Julia set spirals (amber/gold)
    - antigravity: Inverted growth patterns (violet)
    - gpt: Neural network-inspired patterns (cyan/electric blue)
    - gpt_codex: Recursive banyan with aerial roots and jade bark striations
    - gemini: Cosmic botanical patterns (deep indigo/violet)
    """

    # L-System parameters
    axiom: str = "F"
    angle: float = 25.0
    length_ratio: float = 0.7
    branch_probability: float = 0.85
    curve_factor: float = 0.1

    # Visual traits
    color_hue: float = 0.33
    color_saturation: float = 0.7
    stem_thickness: float = 1.0
    leaf_density: float = 0.6

    # Poker traits
    aggression: float = 0.4
    bluff_frequency: float = 0.15
    risk_tolerance: float = 0.5

    # Energy traits
    base_energy_rate: float = 0.02
    growth_efficiency: float = 1.0
    nectar_threshold_ratio: float = 0.75

    # Variant traits
    fractal_type: str = "lsystem"

    # Floral/nectar fractal traits - determines how nectar looks
    floral_type: str = "rose"  # rose, mandelbrot, dahlia, sunflower, chrysanthemum
    floral_petals: int = 5  # Number of petals/lobes (3-12)
    floral_layers: int = 3  # Depth/layers of the flower (1-5)
    floral_spin: float = 0.3  # Rotation/spiral factor (0-1)
    floral_hue: float = 0.95  # Base color hue (0-1), defaults to red/pink
    floral_saturation: float = 0.8  # Color saturation (0-1)

    # Fitness tracking
    fitness_score: float = field(default=0.0)

    _production_rules: List[Tuple[str, str, float]] = field(default_factory=list)

    def __post_init__(self):
        if not self._production_rules:
            self._production_rules = self._generate_default_rules()

    def _generate_default_rules(self) -> List[Tuple[str, str, float]]:
        rules: List[Tuple[str, str, float]] = []
        if self.branch_probability > 0.8:
            rules.append(("F", "FF-[-F+F+F]+[+F-F-F]", 0.7))
            rules.append(("F", "F[-F][+F]", 0.3))
        elif self.branch_probability > 0.6:
            rules.append(("F", "F[-F]+F", 0.5))
            rules.append(("F", "F[+F]-F", 0.5))
        else:
            rules.append(("F", "FF", 0.6))
            rules.append(("F", "F[-F]", 0.4))
        return rules

    def get_production_rules(self) -> Dict[str, List[Tuple[str, float]]]:
        rules: Dict[str, List[Tuple[str, float]]] = {}
        for inp, out, prob in self._production_rules:
            rules.setdefault(inp, []).append((out, prob))
        return rules

    def apply_production(self, input_str: str, rng: Optional[random.Random] = None) -> str:
        rng = rng or random
        rules = self.get_production_rules()
        out = []
        for ch in input_str:
            if ch in rules:
                options = rules[ch]
                total = sum(p for _, p in options)
                r = rng.random() * total
                cum = 0.0
                chosen = ch
                for repl, p in options:
                    cum += p
                    if r <= cum:
                        chosen = repl
                        break
                out.append(chosen)
            else:
                out.append(ch)
        return "".join(out)

    def generate_lsystem_string(self, iterations: int) -> str:
        s = self.axiom
        for _ in range(iterations):
            s = self.apply_production(s)
        return s

    @classmethod
    def create_random(cls, rng: Optional[random.Random] = None) -> "PlantGenome":
        """Create a random L-system plant genome."""
        rng = rng or random

        # Strong bias toward verdant hues so most new plants start green, while
        # still leaving room for occasional surprise palettes in the initial
        # population.
        if rng.random() < 0.95:
            color_hue = rng.uniform(0.25, 0.45)  # Green range
        else:
            color_hue = rng.uniform(0.0, 1.0)  # Rare off-green seedling

        g = cls(
            axiom="F",
            angle=rng.uniform(15.0, 45.0),
            length_ratio=rng.uniform(0.5, 0.85),
            branch_probability=rng.uniform(0.6, 1.0),
            curve_factor=rng.uniform(0.0, 0.3),
            color_hue=color_hue,
            color_saturation=rng.uniform(0.4, 1.0),
            stem_thickness=rng.uniform(0.5, 1.5),
            leaf_density=rng.uniform(0.3, 1.0),
            aggression=rng.uniform(0.2, 0.8),
            bluff_frequency=rng.uniform(0.0, 0.4),
            risk_tolerance=rng.uniform(0.2, 0.8),
            base_energy_rate=rng.uniform(0.01, 0.04),
            growth_efficiency=rng.uniform(0.6, 1.4),
            nectar_threshold_ratio=rng.uniform(0.6, 0.9),
            fractal_type="lsystem",
            # Random floral traits - favor psychedelic patterns
            floral_type=rng.choice([
                # Psychedelic patterns
                "spiral", "julia", "vortex", "starburst", "hypno",
                "spiral", "julia", "vortex", "starburst", "hypno",
                # Fractal (mandelbrot only)
                "mandelbrot", "mandelbrot", "sunflower",
            ]),
            floral_petals=rng.randint(3, 12),
            floral_layers=rng.randint(2, 5),
            floral_spin=rng.uniform(0.3, 1.0),  # More spin for animation
            # Full rainbow of colors
            floral_hue=rng.uniform(0.0, 1.0),
            floral_saturation=rng.uniform(0.7, 1.0),
        )
        g._production_rules = g._generate_default_rules()
        return g

    @classmethod
    def create_cosmic_fern_variant(cls, rng: Optional[random.Random] = None) -> "PlantGenome":
        """Create a Cosmic Fern plant - deep space colors with complex fern structure."""
        rng = rng or random
        g = cls(
            axiom="X",
            angle=rng.uniform(20.0, 30.0),
            length_ratio=rng.uniform(0.55, 0.65),
            branch_probability=rng.uniform(0.88, 0.98),
            curve_factor=rng.uniform(0.1, 0.2),
            color_hue=rng.uniform(0.7, 0.85),  # Deep Purple/Violet/Cosmic range
            color_saturation=rng.uniform(0.8, 1.0),
            stem_thickness=rng.uniform(0.8, 1.2),
            leaf_density=rng.uniform(0.6, 0.9),
            aggression=rng.uniform(0.3, 0.6),
            bluff_frequency=rng.uniform(0.1, 0.3),
            risk_tolerance=rng.uniform(0.4, 0.7),
            base_energy_rate=rng.uniform(0.025, 0.045),
            growth_efficiency=rng.uniform(1.0, 1.4),
            nectar_threshold_ratio=rng.uniform(0.6, 0.8),
            fractal_type="cosmic_fern",
        )
        # Complex 3D fern rules
        g._production_rules = [
            ("X", "F-[[X]+X]+F[+FX]-X", 0.6),
            ("X", "F+[[X]-X]-F[-FX]+X", 0.4),
            ("F", "FF", 1.0),
        ]
        return g

    @classmethod
    def create_claude_variant(cls, rng: Optional[random.Random] = None) -> "PlantGenome":
        """Create a Claude variant - Radiant helix with sunburst whorls."""
        rng = rng or random
        g = cls(
            axiom="X",
            angle=rng.uniform(18.0, 24.0),
            length_ratio=rng.uniform(0.62, 0.72),
            branch_probability=rng.uniform(0.92, 1.0),
            curve_factor=rng.uniform(0.18, 0.32),
            color_hue=rng.uniform(0.1, 0.14),
            color_saturation=rng.uniform(0.78, 0.95),
            stem_thickness=rng.uniform(1.05, 1.45),
            leaf_density=rng.uniform(0.58, 0.82),
            aggression=rng.uniform(0.33, 0.58),
            bluff_frequency=rng.uniform(0.1, 0.24),
            risk_tolerance=rng.uniform(0.42, 0.66),
            base_energy_rate=rng.uniform(0.026, 0.05),
            growth_efficiency=rng.uniform(1.05, 1.5),
            nectar_threshold_ratio=rng.uniform(0.56, 0.82),
            fractal_type="claude",
        )
        g._production_rules = [
            ("X", "F[+X][++X]F[-X][--X]FX", 0.55),
            ("X", "F[+X][-X]F[+FX][-FX]", 0.45),
            ("X", "F[+X][-X]F[+FX][-FX]", 0.45),
            ("F", "FF", 1.0),
        ]
        return g

    @classmethod
    def create_antigravity_variant(cls, rng: Optional[random.Random] = None) -> "PlantGenome":
        """Create an Antigravity variant - Floating vines with aerial roots."""
        rng = rng or random
        g = cls(
            axiom="RX",
            angle=rng.uniform(28.0, 38.0),
            length_ratio=rng.uniform(0.68, 0.82),
            branch_probability=rng.uniform(0.82, 0.95),
            curve_factor=rng.uniform(0.18, 0.32),
            color_hue=rng.uniform(0.78, 0.9),
            color_saturation=rng.uniform(0.85, 1.0),
            stem_thickness=rng.uniform(0.78, 1.15),
            leaf_density=rng.uniform(0.32, 0.58),
            aggression=rng.uniform(0.64, 0.82),
            bluff_frequency=rng.uniform(0.26, 0.36),
            risk_tolerance=rng.uniform(0.72, 0.86),
            base_energy_rate=rng.uniform(0.032, 0.042),
            growth_efficiency=rng.uniform(1.08, 1.32),
            nectar_threshold_ratio=rng.uniform(0.66, 0.76),
            fractal_type="antigravity",
        )
        g._production_rules = [
            ("X", "F[+&FX][-&FX]F", 0.5),
            ("X", "F[+FX]F[-F&X]F", 0.5),
            ("F", "FF-[-F&F]+[+F]", 0.45),
            ("F", "F[&F]F", 0.55),
        ]
        return g

    @classmethod
    def create_gpt_variant(cls, rng: Optional[random.Random] = None) -> "PlantGenome":
        """Create a GPT variant - Lattice bush with mirrored logic branches."""
        rng = rng or random
        g = cls(
            axiom="X",
            angle=rng.uniform(22.0, 32.0),
            length_ratio=rng.uniform(0.58, 0.68),
            branch_probability=rng.uniform(0.9, 1.0),
            curve_factor=rng.uniform(0.1, 0.2),
            color_hue=rng.uniform(0.52, 0.6),
            color_saturation=rng.uniform(0.82, 1.0),
            stem_thickness=rng.uniform(1.25, 1.65),
            leaf_density=rng.uniform(0.62, 0.9),
            aggression=rng.uniform(0.46, 0.72),
            bluff_frequency=rng.uniform(0.16, 0.32),
            risk_tolerance=rng.uniform(0.52, 0.76),
            base_energy_rate=rng.uniform(0.023, 0.043),
            growth_efficiency=rng.uniform(0.98, 1.36),
            nectar_threshold_ratio=rng.uniform(0.6, 0.8),
            fractal_type="gpt",
        )
        g._production_rules = [
            ("X", "F[+X]F[-X]|F[+X][-X]", 0.5),
            ("X", "F[+X][-X]FX", 0.3),
            ("X", "F[+X][-X]F", 0.2),
            ("F", "FF", 0.6),
            ("F", "Ff", 0.4),
        ]
        return g

    @classmethod
    def create_gpt_codex_variant(cls, rng: Optional[random.Random] = None) -> "PlantGenome":
        """Create a GPT-5.1 Codex banyan with aerial roots and jade bark."""
        rng = rng or random
        g = cls(
            axiom="X",
            angle=rng.uniform(26.0, 32.0),
            length_ratio=rng.uniform(0.64, 0.74),
            branch_probability=rng.uniform(0.82, 0.96),
            curve_factor=rng.uniform(0.12, 0.22),
            color_hue=rng.uniform(0.32, 0.38),  # Cool jade core
            color_saturation=rng.uniform(0.65, 0.85),
            stem_thickness=rng.uniform(1.0, 1.35),
            leaf_density=rng.uniform(0.55, 0.85),
            aggression=rng.uniform(0.28, 0.5),
            bluff_frequency=rng.uniform(0.14, 0.3),
            risk_tolerance=rng.uniform(0.38, 0.65),
            base_energy_rate=rng.uniform(0.022, 0.042),
            growth_efficiency=rng.uniform(1.05, 1.45),
            nectar_threshold_ratio=rng.uniform(0.62, 0.82),
            fractal_type="gpt_codex",
        )
        g._production_rules = [
            ("X", "F[+X][-X]R[&FX]", 0.4),
            ("X", "F[+R][-R]X", 0.3),
            ("X", "FF[+FX][-FX]", 0.2),
            ("R", "F[&F]f", 0.1),
            ("F", "FF", 1.0),
        ]
        return g

    @classmethod
    def create_gemini_variant(cls, rng: Optional[random.Random] = None) -> "PlantGenome":
        """Create a Gemini 3Pro plant - cosmic botanical with deep indigo/violet hues.

        This variant features highly complex, "multimodal" branching patterns that
        represent the model's ability to process diverse information types.
        The aesthetic is "Deep Space" - dark, rich colors with high saturation.
        """
        rng = rng or random
        g = cls(
            axiom="X",
            angle=rng.uniform(20.0, 30.0),
            length_ratio=rng.uniform(0.6, 0.7),
            branch_probability=rng.uniform(0.85, 0.98),
            curve_factor=rng.uniform(0.1, 0.25),
            color_hue=rng.uniform(0.75, 0.82),  # Deep Indigo/Violet range
            color_saturation=rng.uniform(0.8, 1.0),
            stem_thickness=rng.uniform(0.8, 1.2),
            leaf_density=rng.uniform(0.7, 0.9),
            aggression=rng.uniform(0.4, 0.6),
            bluff_frequency=rng.uniform(0.1, 0.3),
            risk_tolerance=rng.uniform(0.4, 0.7),
            base_energy_rate=rng.uniform(0.025, 0.045),
            growth_efficiency=rng.uniform(1.0, 1.4),
            nectar_threshold_ratio=rng.uniform(0.6, 0.8),
            fractal_type="gemini",
        )
        # Complex, multimodal branching rules
        g._production_rules = [
            ("X", "F-[[X]+X]+F[+FX]-X", 0.5),  # Standard fern-like
            ("X", "F[+X][-X]FX", 0.3),         # Dense cluster
            ("F", "FF", 0.8),                  # Growth
            ("F", "F[+F]F[-F]F", 0.2),         # Extra branching on stems
        ]
        return g

    @classmethod
    def create_sonnet_variant(cls, rng: Optional[random.Random] = None) -> "PlantGenome":
        """Create a Sonnet 4.5 plant - elegant botanical fern with coral/terracotta hues.

        This variant uses proper L-system rules that produce actual plant-like
        structures (ferns, bushes, trees) rather than abstract mathematical fractals.
        The aesthetic emphasizes organic beauty, natural branching patterns, and
        graceful asymmetry - representing the thoughtful, balanced nature of Sonnet.
        """
        rng = rng or random
        g = cls(
            axiom="X",  # Use X axiom for fern-like growth
            angle=rng.uniform(22.0, 28.0),  # Tighter angles for elegant fronds
            length_ratio=rng.uniform(0.65, 0.75),  # Balanced reduction for visible structure
            branch_probability=rng.uniform(0.85, 0.95),
            curve_factor=rng.uniform(0.12, 0.22),  # Natural curvature
            color_hue=rng.uniform(0.02, 0.08),  # Coral/terracotta range
            color_saturation=rng.uniform(0.65, 0.85),
            stem_thickness=rng.uniform(0.9, 1.2),
            leaf_density=rng.uniform(0.7, 0.95),  # Dense foliage
            aggression=rng.uniform(0.3, 0.5),  # Balanced poker style
            bluff_frequency=rng.uniform(0.1, 0.25),
            risk_tolerance=rng.uniform(0.35, 0.55),
            base_energy_rate=rng.uniform(0.025, 0.045),
            growth_efficiency=rng.uniform(1.0, 1.4),
            nectar_threshold_ratio=rng.uniform(0.6, 0.8),
            fractal_type="sonnet",
        )
        # Classic botanical L-system rules that produce fern-like structures
        # These create natural, organic branching patterns
        g._production_rules = [
            # Primary fern frond pattern - creates elegant recursive branching
            ("X", "F+[[X]-X]-F[-FX]+X", 0.55),
            # Secondary pattern - more upright growth
            ("X", "F-[[X]+X]+F[+FX]-X", 0.35),
            # Simple elongation for variety
            ("X", "FX", 0.10),
            # Stem extension
            ("F", "FF", 1.0),
        ]
        return g

    @classmethod
    def from_parent(
        cls,
        parent: "PlantGenome",
        mutation_rate: float = 0.15,
        mutation_strength: float = 0.15,
        rng: Optional[random.Random] = None,
    ) -> "PlantGenome":
        """Create offspring genome with mutations while preserving variant identity."""
        rng = rng or random

        def mutate_float(val: float, min_val: float, max_val: float) -> float:
            if rng.random() < mutation_rate:
                val += rng.gauss(0, mutation_strength * (max_val - min_val))
            return max(min_val, min(max_val, val))

        def mutate_color(val: float, min_val: float, max_val: float) -> float:
            # Default drift within the variant's palette
            val = mutate_float(val, min_val, max_val)

            # Rarely allow a full-spectrum mutation so lineages can explore new hues
            if rng.random() < mutation_rate * 0.5:
                val = rng.uniform(0.0, 1.0)

            return max(0.0, min(1.0, val))

        # Determine color mutation range based on variant to preserve identity
        if parent.fractal_type == "claude":
            color_min, color_max = 0.05, 0.18  # Golden range
        elif parent.fractal_type == "cosmic_fern":
            color_min, color_max = 0.65, 0.90  # Cosmic purple/violet range
        elif parent.fractal_type == "antigravity":
            color_min, color_max = 0.65, 0.90  # Violet range
        elif parent.fractal_type == "gpt":
            color_min, color_max = 0.45, 0.58  # Cyan range
        elif parent.fractal_type == "gpt_codex":
            color_min, color_max = 0.30, 0.42  # Cool jade with teal ink range
        elif parent.fractal_type == "sonnet":
            color_min, color_max = 0.0, 0.12  # Coral/terracotta range
        elif parent.fractal_type == "gemini":
            color_min, color_max = 0.75, 0.82  # Deep Indigo/Violet range
        else:
            color_min, color_max = 0.20, 0.50  # Green range for lsystem

        # Floral type can rarely mutate to a different type
        floral_type = parent.floral_type
        if rng.random() < mutation_rate * 0.3:
            floral_type = rng.choice([
                # Psychedelic patterns
                "spiral", "julia", "vortex", "starburst", "hypno",
                "spiral", "julia", "vortex", "starburst", "hypno",
                # Fractal (mandelbrot only)
                "mandelbrot", "mandelbrot", "sunflower",
            ])

        def mutate_int(val: int, min_val: int, max_val: int) -> int:
            if rng.random() < mutation_rate:
                val += rng.choice([-1, 1])
            return max(min_val, min(max_val, val))

        offspring = cls(
            axiom=parent.axiom,
            angle=mutate_float(parent.angle, 15.0, 45.0),
            length_ratio=mutate_float(parent.length_ratio, 0.5, 0.85),
            branch_probability=mutate_float(parent.branch_probability, 0.6, 1.0),
            curve_factor=mutate_float(parent.curve_factor, 0.0, 0.3),
            color_hue=mutate_color(parent.color_hue, color_min, color_max),
            color_saturation=mutate_float(parent.color_saturation, 0.4, 1.0),
            stem_thickness=mutate_float(parent.stem_thickness, 0.5, 1.5),
            leaf_density=mutate_float(parent.leaf_density, 0.3, 1.0),
            aggression=mutate_float(parent.aggression, 0.0, 1.0),
            bluff_frequency=mutate_float(parent.bluff_frequency, 0.0, 0.5),
            risk_tolerance=mutate_float(parent.risk_tolerance, 0.2, 0.8),
            base_energy_rate=mutate_float(parent.base_energy_rate, 0.01, 0.05),
            growth_efficiency=mutate_float(parent.growth_efficiency, 0.5, 1.5),
            nectar_threshold_ratio=mutate_float(parent.nectar_threshold_ratio, 0.6, 0.9),
            fractal_type=parent.fractal_type,  # Preserve variant type
            # Inherit and mutate floral traits
            floral_type=floral_type,
            floral_petals=mutate_int(parent.floral_petals, 3, 12),
            floral_layers=mutate_int(parent.floral_layers, 1, 5),
            floral_spin=mutate_float(parent.floral_spin, 0.0, 1.0),
            floral_hue=mutate_float(parent.floral_hue, 0.0, 1.0),
            floral_saturation=mutate_float(parent.floral_saturation, 0.5, 1.0),
            fitness_score=0.0,
        )

        # Copy parent's production rules and potentially mutate
        offspring._production_rules = list(parent._production_rules)
        if rng.random() < mutation_rate * 2:
            offspring._mutate_production_rules(rng)
        return offspring

    def _mutate_production_rules(self, rng: random.Random) -> None:
        if not self._production_rules:
            return
        idx = rng.randint(0, len(self._production_rules) - 1)
        input_char, output, prob = self._production_rules[idx]
        mutation_type = rng.choice(["angle_change", "branch_add", "length_change"])
        if mutation_type == "angle_change":
            if "+" in output or "-" in output:
                out_list = list(output)
                for i, c in enumerate(out_list):
                    if c in "+-" and rng.random() < 0.3:
                        out_list[i] = "-" if c == "+" else "+"
                output = "".join(out_list)
        elif mutation_type == "branch_add":
            if rng.random() < 0.5 and "[" not in output:
                insert_pos = rng.randint(1, len(output))
                branch = "[" + rng.choice(["+F", "-F", "F"]) + "]"
                output = output[:insert_pos] + branch + output[insert_pos:]
            elif "[" in output and rng.random() < 0.3:
                output = output.replace("[-F]", "", 1)
        elif mutation_type == "length_change":
            if rng.random() < 0.5:
                output = output.replace("F", "FF", 1)
            else:
                output = output.replace("FF", "F", 1)
        self._production_rules[idx] = (input_char, output, prob)

    def update_fitness(
        self,
        energy_gained: float = 0.0,
        survived_frames: int = 0,
        nectar_produced: int = 0,
        poker_won: int = 0,
    ) -> None:
        """Update fitness score based on performance metrics."""
        self.fitness_score += (
            energy_gained * 1.0
            + survived_frames * 0.005
            + nectar_produced * 30.0
            + poker_won * 20.0
        )

    def get_color_rgb(self) -> Tuple[int, int, int]:
        h = self.color_hue
        s = self.color_saturation
        l = 0.4
        if s == 0:
            r = g = b = int(l * 255)
        else:
            def hue_to_rgb(p: float, q: float, t: float) -> float:
                if t < 0:
                    t += 1
                if t > 1:
                    t -= 1
                if t < 1 / 6:
                    return p + (q - p) * 6 * t
                if t < 1 / 2:
                    return q
                if t < 2 / 3:
                    return p + (q - p) * (2 / 3 - t) * 6
                return p

            q = l * (1 + s) if l < 0.5 else l + s - l * s
            p = 2 * l - q
            r = int(hue_to_rgb(p, q, h + 1 / 3) * 255)
            g = int(hue_to_rgb(p, q, h) * 255)
            b = int(hue_to_rgb(p, q, h - 1 / 3) * 255)
        return (r, g, b)

    def to_dict(self) -> Dict:
        return {
            "axiom": self.axiom,
            "angle": self.angle,
            "length_ratio": self.length_ratio,
            "branch_probability": self.branch_probability,
            "curve_factor": self.curve_factor,
            "color_hue": self.color_hue,
            "color_saturation": self.color_saturation,
            "stem_thickness": self.stem_thickness,
            "leaf_density": self.leaf_density,
            "aggression": self.aggression,
            "bluff_frequency": self.bluff_frequency,
            "risk_tolerance": self.risk_tolerance,
            "base_energy_rate": self.base_energy_rate,
            "growth_efficiency": self.growth_efficiency,
            "nectar_threshold_ratio": self.nectar_threshold_ratio,
            "fitness_score": self.fitness_score,
            "fractal_type": self.fractal_type,
            # Floral traits
            "floral_type": self.floral_type,
            "floral_petals": self.floral_petals,
            "floral_layers": self.floral_layers,
            "floral_spin": self.floral_spin,
            "floral_hue": self.floral_hue,
            "floral_saturation": self.floral_saturation,
            "production_rules": [
                {"input": inp, "output": out, "prob": prob}
                for inp, out, prob in self._production_rules
            ],
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "PlantGenome":
        rules = [
            (r["input"], r["output"], r["prob"])
            for r in data.get("production_rules", [])
        ]
        g = cls(
            axiom=data.get("axiom", "F"),
            angle=data.get("angle", 25.0),
            length_ratio=data.get("length_ratio", 0.7),
            branch_probability=data.get("branch_probability", 0.85),
            curve_factor=data.get("curve_factor", 0.1),
            color_hue=data.get("color_hue", 0.33),
            color_saturation=data.get("color_saturation", 0.7),
            stem_thickness=data.get("stem_thickness", 1.0),
            leaf_density=data.get("leaf_density", 0.6),
            aggression=data.get("aggression", 0.4),
            bluff_frequency=data.get("bluff_frequency", 0.15),
            risk_tolerance=data.get("risk_tolerance", 0.5),
            base_energy_rate=data.get("base_energy_rate", 0.02),
            growth_efficiency=data.get("growth_efficiency", 1.0),
            nectar_threshold_ratio=data.get("nectar_threshold_ratio", 0.75),
            fitness_score=data.get("fitness_score", 0.0),
            fractal_type=data.get("fractal_type", "lsystem"),
            # Floral traits
            floral_type=data.get("floral_type", "rose"),
            floral_petals=data.get("floral_petals", 5),
            floral_layers=data.get("floral_layers", 3),
            floral_spin=data.get("floral_spin", 0.3),
            floral_hue=data.get("floral_hue", 0.95),
            floral_saturation=data.get("floral_saturation", 0.8),
        )
        if rules:
            g._production_rules = rules
        else:
            g._production_rules = g._generate_default_rules()
        return g
