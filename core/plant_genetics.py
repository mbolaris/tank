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
    - mandelbrot: Mandelbrot set fractals (purple)
    - claude: Golden Julia set spirals (amber/gold)
    - antigravity: Inverted growth patterns (violet)
    - gpt: Neural network-inspired patterns (cyan/electric blue)
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
        g = cls(
            axiom="F",
            angle=rng.uniform(15.0, 45.0),
            length_ratio=rng.uniform(0.5, 0.85),
            branch_probability=rng.uniform(0.6, 1.0),
            curve_factor=rng.uniform(0.0, 0.3),
            color_hue=rng.uniform(0.25, 0.45),  # Green range
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
        )
        g._production_rules = g._generate_default_rules()
        return g

    @classmethod
    def create_mandelbrot_variant(cls, rng: Optional[random.Random] = None) -> "PlantGenome":
        """Create a Mandelbrot set plant - deep purples with mathematical beauty."""
        rng = rng or random
        g = cls(
            axiom="F",
            angle=rng.uniform(20.0, 35.0),
            length_ratio=rng.uniform(0.6, 0.8),
            branch_probability=rng.uniform(0.7, 0.95),
            curve_factor=rng.uniform(0.05, 0.2),
            color_hue=rng.uniform(0.55, 0.75),  # Purple range
            color_saturation=rng.uniform(0.6, 1.0),
            stem_thickness=rng.uniform(0.9, 1.3),
            leaf_density=rng.uniform(0.4, 0.8),
            aggression=rng.uniform(0.2, 0.6),
            bluff_frequency=rng.uniform(0.05, 0.25),
            risk_tolerance=rng.uniform(0.3, 0.7),
            base_energy_rate=rng.uniform(0.02, 0.045),
            growth_efficiency=rng.uniform(0.9, 1.4),
            nectar_threshold_ratio=rng.uniform(0.6, 0.85),
            fractal_type="mandelbrot",
        )
        g._production_rules = g._generate_default_rules()
        return g

    @classmethod
    def create_claude_variant(cls, rng: Optional[random.Random] = None) -> "PlantGenome":
        """Create a Claude plant - golden Julia spirals with Fibonacci aesthetics."""
        rng = rng or random
        g = cls(
            axiom="F",
            angle=rng.uniform(32.0, 42.0),
            length_ratio=rng.uniform(0.58, 0.68),
            branch_probability=rng.uniform(0.75, 0.95),
            curve_factor=rng.uniform(0.15, 0.28),
            color_hue=rng.uniform(0.08, 0.14),  # Golden/amber range
            color_saturation=rng.uniform(0.75, 0.95),
            stem_thickness=rng.uniform(0.85, 1.2),
            leaf_density=rng.uniform(0.5, 0.85),
            aggression=rng.uniform(0.35, 0.55),
            bluff_frequency=rng.uniform(0.08, 0.22),
            risk_tolerance=rng.uniform(0.4, 0.65),
            base_energy_rate=rng.uniform(0.025, 0.048),
            growth_efficiency=rng.uniform(1.0, 1.45),
            nectar_threshold_ratio=rng.uniform(0.55, 0.8),
            fractal_type="claude",
        )
        g._production_rules = g._generate_default_rules()
        return g

    @classmethod
    def create_antigravity_variant(cls, rng: Optional[random.Random] = None) -> "PlantGenome":
        """Create an Antigravity plant - unusual inverted growth with violet hues."""
        rng = rng or random
        g = cls(
            axiom="X",
            angle=rng.uniform(18.0, 25.0),
            length_ratio=0.6,
            branch_probability=0.9,
            curve_factor=0.15,
            color_hue=rng.uniform(0.7, 0.85),  # Violet range
            color_saturation=0.9,
            stem_thickness=1.2,
            leaf_density=0.8,
            aggression=0.7,
            bluff_frequency=0.3,
            risk_tolerance=0.8,
            base_energy_rate=0.035,
            growth_efficiency=1.2,
            nectar_threshold_ratio=0.7,
            fractal_type="antigravity",
        )
        g._production_rules = [
            ("X", "F-[[X]+X]+F[+FX]-X", 1.0),
            ("F", "FF", 1.0),
        ]
        return g

    @classmethod
    def create_gpt_variant(cls, rng: Optional[random.Random] = None) -> "PlantGenome":
        """Create a GPT plant - neural network-inspired with electric cyan/blue patterns."""
        rng = rng or random
        g = cls(
            axiom="F",
            angle=rng.uniform(28.0, 38.0),
            length_ratio=rng.uniform(0.62, 0.72),
            branch_probability=rng.uniform(0.8, 0.98),  # High branching for "neural" look
            curve_factor=rng.uniform(0.08, 0.18),
            color_hue=rng.uniform(0.48, 0.55),  # Cyan/teal range
            color_saturation=rng.uniform(0.8, 1.0),
            stem_thickness=rng.uniform(0.7, 1.1),
            leaf_density=rng.uniform(0.6, 0.9),
            aggression=rng.uniform(0.45, 0.7),  # More aggressive poker
            bluff_frequency=rng.uniform(0.15, 0.35),  # Higher bluff rate
            risk_tolerance=rng.uniform(0.5, 0.75),
            base_energy_rate=rng.uniform(0.022, 0.042),
            growth_efficiency=rng.uniform(0.95, 1.35),
            nectar_threshold_ratio=rng.uniform(0.58, 0.78),
            fractal_type="gpt",
        )
        # Neural network-inspired branching patterns
        g._production_rules = [
            ("F", "FF+[+F-F-F]-[-F+F+F]", 0.5),  # Symmetric branching
            ("F", "F[+F]F[-F]F", 0.3),  # Dense connections
            ("F", "F[-F][+F][F]", 0.2),  # Triple branch
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

        # Determine color mutation range based on variant to preserve identity
        if parent.fractal_type == "claude":
            color_min, color_max = 0.05, 0.18  # Golden range
        elif parent.fractal_type == "mandelbrot":
            color_min, color_max = 0.50, 0.80  # Purple range
        elif parent.fractal_type == "antigravity":
            color_min, color_max = 0.65, 0.90  # Violet range
        elif parent.fractal_type == "gpt":
            color_min, color_max = 0.45, 0.58  # Cyan range
        elif parent.fractal_type == "sonnet":
            color_min, color_max = 0.0, 0.12  # Coral/terracotta range
        else:
            color_min, color_max = 0.20, 0.50  # Green range for lsystem

        offspring = cls(
            axiom=parent.axiom,
            angle=mutate_float(parent.angle, 15.0, 45.0),
            length_ratio=mutate_float(parent.length_ratio, 0.5, 0.85),
            branch_probability=mutate_float(parent.branch_probability, 0.6, 1.0),
            curve_factor=mutate_float(parent.curve_factor, 0.0, 0.3),
            color_hue=mutate_float(parent.color_hue, color_min, color_max),
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
        )
        if rules:
            g._production_rules = rules
        else:
            g._production_rules = g._generate_default_rules()
        return g
