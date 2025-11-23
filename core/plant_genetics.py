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

    See module-level documentation for an overview of traits.
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
        rng = rng or random
        g = cls(
            axiom="F",
            angle=rng.uniform(15.0, 45.0),
            length_ratio=rng.uniform(0.5, 0.85),
            branch_probability=rng.uniform(0.6, 1.0),
            curve_factor=rng.uniform(0.0, 0.3),
            color_hue=rng.uniform(0.25, 0.45),
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
        rng = rng or random
        g = cls(
            axiom="F",
            angle=rng.uniform(20.0, 35.0),
            length_ratio=rng.uniform(0.6, 0.8),
            branch_probability=rng.uniform(0.7, 0.95),
            curve_factor=rng.uniform(0.05, 0.2),
            color_hue=rng.uniform(0.55, 0.75),
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
        rng = rng or random
        # Golden ratio for proportions
        phi = 1.618033988749895
        g = cls(
            axiom="F",
            angle=rng.uniform(32.0, 42.0),
            length_ratio=rng.uniform(0.58, 0.68),
            branch_probability=rng.uniform(0.75, 0.95),
            curve_factor=rng.uniform(0.15, 0.28),
            color_hue=rng.uniform(0.08, 0.14),
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
        rng = rng or random
        g = cls(
            axiom="X",
            angle=rng.uniform(18.0, 25.0),
            length_ratio=0.6,
            branch_probability=0.9,
            curve_factor=0.15,
            color_hue=rng.uniform(0.7, 0.85),
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
    def from_parent(
        cls,
        parent: "PlantGenome",
        mutation_rate: float = 0.15,
        mutation_strength: float = 0.15,
        rng: Optional[random.Random] = None,
    ) -> "PlantGenome":
        rng = rng or random

        def mutate_float(val: float, min_val: float, max_val: float) -> float:
            if rng.random() < mutation_rate:
                val += rng.gauss(0, mutation_strength * (max_val - min_val))
            return max(min_val, min(max_val, val))

        offspring = cls(
            axiom=parent.axiom,
            angle=mutate_float(parent.angle, 15.0, 45.0),
            length_ratio=mutate_float(parent.length_ratio, 0.5, 0.85),
            branch_probability=mutate_float(parent.branch_probability, 0.6, 1.0),
            curve_factor=mutate_float(parent.curve_factor, 0.0, 0.3),
            color_hue=mutate_float(parent.color_hue, 0.2, 0.5),
            color_saturation=mutate_float(parent.color_saturation, 0.4, 1.0),
            stem_thickness=mutate_float(parent.stem_thickness, 0.5, 1.5),
            leaf_density=mutate_float(parent.leaf_density, 0.3, 1.0),
            aggression=mutate_float(parent.aggression, 0.0, 1.0),
            bluff_frequency=mutate_float(parent.bluff_frequency, 0.0, 0.5),
            risk_tolerance=mutate_float(parent.risk_tolerance, 0.2, 0.8),
            base_energy_rate=mutate_float(parent.base_energy_rate, 0.01, 0.05),
            growth_efficiency=mutate_float(parent.growth_efficiency, 0.5, 1.5),
            nectar_threshold_ratio=mutate_float(parent.nectar_threshold_ratio, 0.6, 0.9),
            fractal_type=parent.fractal_type,
            fitness_score=0.0,
        )
        offspring._production_rules = offspring._generate_default_rules()
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

    def update_fitness(self, energy_gained: float = 0.0, survived_frames: int = 0, nectar_produced: int = 0, poker_won: int = 0) -> None:
        self.fitness_score += (
            energy_gained * 1.0 + survived_frames * 0.005 + nectar_produced * 30.0 + poker_won * 20.0
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
                if t < 1/6:
                    return p + (q - p) * 6 * t
                if t < 1/2:
                    return q
                if t < 2/3:
                    return p + (q - p) * (2/3 - t) * 6
                return p
            q = l * (1 + s) if l < 0.5 else l + s - l * s
            p = 2 * l - q
            r = int(hue_to_rgb(p, q, h + 1/3) * 255)
            g = int(hue_to_rgb(p, q, h) * 255)
            b = int(hue_to_rgb(p, q, h - 1/3) * 255)
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
            "production_rules": [{"input": inp, "output": out, "prob": prob} for inp, out, prob in self._production_rules],
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "PlantGenome":
        rules = [(r["input"], r["output"], r["prob"]) for r in data.get("production_rules", [])]
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

    L-System Parameters (control fractal shape):
        axiom: Starting string for L-system (default "F")
        angle: Branching angle in degrees (15-45)
        length_ratio: Length reduction per iteration (0.5-0.9)
        branch_probability: Chance of branching at each node (0.6-1.0)
        curve_factor: How much branches curve (0.0-0.3)

    Visual Traits:
        color_hue: Base color hue (0.0-1.0, maps to green spectrum)
        color_saturation: Color intensity (0.4-1.0)
        stem_thickness: Base stem width multiplier (0.5-1.5)
        leaf_density: How many leaf nodes to render (0.3-1.0)

    Poker Traits:
        aggression: Poker betting aggression (0.0-1.0)
        bluff_frequency: How often to bluff (0.0-0.5)
        risk_tolerance: Willingness to call large bets (0.2-0.8)

    Energy Traits:
        base_energy_rate: Passive energy gain per frame (0.01-0.05)
        growth_efficiency: How much energy converts to size (0.5-1.5)
        nectar_threshold_ratio: Energy ratio to produce nectar (0.6-0.9)

    Fractal Variants:
        fractal_type: Rendering style for the plant's fractal (e.g., 'lsystem', 'mandelbrot')

    Fitness:
        fitness_score: Accumulated fitness over lifetime
    """

    # L-System parameters
    def create_claude_variant(
        cls, rng: Optional["random.Random"] = None
    ) -> "PlantGenome":
        """Create a Claude-inspired plant genome with golden spiral aesthetics.

        The Claude variant features a Julia set fractal with golden/amber colors,
        representing warmth, creativity, and thoughtful analysis. It uses the
        golden ratio in its visual proportions and has enhanced energy traits
        reflecting Claude's helpful and efficient nature.
        """
        import random as random_module

        rng = rng or random_module

        # Golden ratio for proportions
        phi = 1.618033988749895

        genome = cls(
            axiom="F",
            # Golden angle (137.5 degrees) for Fibonacci spiral aesthetics
            angle=rng.uniform(32.0, 42.0),
            # Length ratio based on inverse golden ratio
            length_ratio=rng.uniform(0.58, 0.68),
            branch_probability=rng.uniform(0.75, 0.95),
            # Higher curve factor for elegant spiraling
            curve_factor=rng.uniform(0.15, 0.28),
            # Golden/amber spectrum (warm, creative)
            color_hue=rng.uniform(0.08, 0.14),
            color_saturation=rng.uniform(0.75, 0.95),
            stem_thickness=rng.uniform(0.85, 1.2),
            leaf_density=rng.uniform(0.5, 0.85),
            # Balanced poker traits (thoughtful, analytical)
            aggression=rng.uniform(0.35, 0.55),
            bluff_frequency=rng.uniform(0.08, 0.22),
            risk_tolerance=rng.uniform(0.4, 0.65),
            # Enhanced energy traits (helpful, efficient)
            base_energy_rate=rng.uniform(0.025, 0.048),
            growth_efficiency=rng.uniform(1.0, 1.45),
            nectar_threshold_ratio=rng.uniform(0.55, 0.8),
            fractal_type="claude",
        )

        genome._production_rules = genome._generate_default_rules()
            # Medium branching
            rules.append(("F", "F[-F]+F", 0.5))
            rules.append(("F", "F[+F]-F", 0.5))
        else:
            # Sparse branching
            rules.append(("F", "FF", 0.6))
            rules.append(("F", "F[-F]", 0.4))

        return rules

    def get_production_rules(self) -> Dict[str, List[Tuple[str, float]]]:
        """Get production rules as a dictionary for L-system processing.

        Returns:
            Dict mapping input chars to list of (output, probability) tuples
        """
        rules: Dict[str, List[Tuple[str, float]]] = {}
        for input_char, output, prob in self._production_rules:
            if input_char not in rules:
                rules[input_char] = []
            rules[input_char].append((output, prob))
        return rules

    def apply_production(self, input_str: str, rng: Optional[random.Random] = None) -> str:
        """Apply one iteration of L-system production rules.

        Args:
            input_str: Current L-system string
            rng: Random number generator

        Returns:
            New string after applying production rules
        """
        rng = rng or random
        rules = self.get_production_rules()
        output = []

        for char in input_str:
            if char in rules:
                # Choose a production based on probabilities
                options = rules[char]
                total_prob = sum(p for _, p in options)
                roll = rng.random() * total_prob
                cumulative = 0.0
                chosen = char  # Default: keep character

                for replacement, prob in options:
                    cumulative += prob
                    if roll <= cumulative:
                        chosen = replacement
                        break

                output.append(chosen)
            else:
                output.append(char)

        return "".join(output)

    def generate_lsystem_string(self, iterations: int) -> str:
        """Generate the full L-system string for rendering.

        Args:
            iterations: Number of production iterations (1-5 typically)

        Returns:
            L-system string ready for interpretation
        """
        result = self.axiom
        for _ in range(iterations):
            result = self.apply_production(result)
        return result

    @classmethod
    def create_random(cls, rng: Optional["random.Random"] = None) -> "PlantGenome":
        """Create a random plant genome.

        Args:
            rng: Random number generator

        Returns:
            New random PlantGenome
        """
        import random as random_module
        rng = rng or random_module

        genome = cls(
            # L-System parameters
            axiom="F",
            angle=rng.uniform(15.0, 45.0),
            length_ratio=rng.uniform(0.5, 0.85),
            branch_probability=rng.uniform(0.6, 1.0),
            curve_factor=rng.uniform(0.0, 0.3),
            # Visual traits
            color_hue=rng.uniform(0.25, 0.45),  # Green spectrum
            color_saturation=rng.uniform(0.4, 1.0),
            stem_thickness=rng.uniform(0.5, 1.5),
            leaf_density=rng.uniform(0.3, 1.0),
            # Poker traits
            aggression=rng.uniform(0.2, 0.8),
            bluff_frequency=rng.uniform(0.0, 0.4),
            risk_tolerance=rng.uniform(0.2, 0.8),
            # Energy traits
            base_energy_rate=rng.uniform(0.01, 0.04),
            growth_efficiency=rng.uniform(0.6, 1.4),
            nectar_threshold_ratio=rng.uniform(0.6, 0.9),
            fractal_type="lsystem",
        )

        # Generate production rules based on branch_probability
        genome._production_rules = genome._generate_default_rules()

        return genome

    @classmethod
    def create_antigravity_variant(
        cls, rng: Optional["random.Random"] = None
    ) -> "PlantGenome":
        """Create the Antigravity LLM signature plant.

        A high-tech, defying-physics plant structure with unique branching and
        vibrant colors.
        """
        import random as random_module

        rng = rng or random_module

        # Antigravity plants are bold, efficient, and slightly aggressive
        genome = cls(
            axiom="X",  # Start with a complex bud
            angle=rng.uniform(18.0, 25.0),
            length_ratio=0.6,
            branch_probability=0.9,
            curve_factor=0.15,
            # Vibrant Purple/Blue/Neon hues
            color_hue=rng.uniform(0.7, 0.85),
            color_saturation=0.9,
            stem_thickness=1.2,
            leaf_density=0.8,
            # High stats for the contest
            aggression=0.7,
            bluff_frequency=0.3,
            risk_tolerance=0.8,
            base_energy_rate=0.035,
            growth_efficiency=1.2,
            nectar_threshold_ratio=0.7,
            fractal_type="antigravity",
        )

        # Custom rules for Antigravity
        # X -> F-[[X]+X]+F[+FX]-X
        # F -> FF
        genome._production_rules = [
            ("X", "F-[[X]+X]+F[+FX]-X", 1.0),
            ("F", "FF", 1.0),
        ]

        return genome

    @classmethod
    def create_mandelbrot_variant(
        cls, rng: Optional["random.Random"] = None
    ) -> "PlantGenome":
        """Create a Mandelbrot-inspired plant genome.

        This variant signals the renderer to use a Mandelbrot set visualization
        and slightly boosts base energy traits to reflect its special status.
        """
        import random as random_module

        rng = rng or random_module

        genome = cls(
            axiom="F",
            angle=rng.uniform(20.0, 35.0),
            length_ratio=rng.uniform(0.6, 0.8),
            branch_probability=rng.uniform(0.7, 0.95),
            curve_factor=rng.uniform(0.05, 0.2),
            color_hue=rng.uniform(0.55, 0.75),
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

        genome._production_rules = genome._generate_default_rules()

        return genome

    @classmethod
<<<<<<< Updated upstream
<<<<<<< Updated upstream
    def create_claude_variant(
        cls, rng: Optional["random.Random"] = None
    ) -> "PlantGenome":
        """Create a Claude-inspired plant genome with golden spiral aesthetics.

        The Claude variant features a Julia set fractal with golden/amber colors,
        representing warmth, creativity, and thoughtful analysis. It uses the
        golden ratio in its visual proportions and has enhanced energy traits
        reflecting Claude's helpful and efficient nature.

        Visual characteristics:
        - Golden/amber color spectrum (warm, approachable)
        - Julia set spiral patterns (elegant mathematical beauty)
        - Fibonacci-inspired leaf arrangements
        - Glowing particle effects (representing ideas)
=======
=======
>>>>>>> Stashed changes
    def create_antigravity_variant(
        cls, rng: Optional["random.Random"] = None
    ) -> "PlantGenome":
        """Create the Antigravity LLM signature plant.

        A high-tech, defying-physics plant structure with
        unique branching and vibrant colors.
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
        """
        import random as random_module

        rng = rng or random_module

<<<<<<< Updated upstream
<<<<<<< Updated upstream
        # Golden ratio for proportions
        phi = 1.618033988749895

        genome = cls(
            axiom="F",
            # Golden angle (137.5 degrees) for Fibonacci spiral aesthetics
            angle=rng.uniform(32.0, 42.0),
            # Length ratio based on inverse golden ratio
            length_ratio=rng.uniform(0.58, 0.68),
            branch_probability=rng.uniform(0.75, 0.95),
            # Higher curve factor for elegant spiraling
            curve_factor=rng.uniform(0.15, 0.28),
            # Golden/amber spectrum (warm, creative)
            color_hue=rng.uniform(0.08, 0.14),
            color_saturation=rng.uniform(0.75, 0.95),
            stem_thickness=rng.uniform(0.85, 1.2),
            leaf_density=rng.uniform(0.5, 0.85),
            # Balanced poker traits (thoughtful, analytical)
            aggression=rng.uniform(0.35, 0.55),
            bluff_frequency=rng.uniform(0.08, 0.22),
            risk_tolerance=rng.uniform(0.4, 0.65),
            # Enhanced energy traits (helpful, efficient)
            base_energy_rate=rng.uniform(0.025, 0.048),
            growth_efficiency=rng.uniform(1.0, 1.45),
            nectar_threshold_ratio=rng.uniform(0.55, 0.8),
            fractal_type="claude",
        )

        genome._production_rules = genome._generate_default_rules()
=======
=======
>>>>>>> Stashed changes
        # Antigravity plants are bold, efficient, and slightly aggressive
        genome = cls(
            axiom="X",  # Start with a complex bud
            angle=rng.uniform(18.0, 25.0),
            length_ratio=0.6,
            branch_probability=0.9,
            curve_factor=0.15,
            # Vibrant Purple/Blue/Neon hues
            color_hue=rng.uniform(0.7, 0.85),
            color_saturation=0.9,
            stem_thickness=1.2,
            leaf_density=0.8,
            # High stats for the contest
            aggression=0.7,
            bluff_frequency=0.3,
            risk_tolerance=0.8,
            base_energy_rate=0.035,
            growth_efficiency=1.2,
            nectar_threshold_ratio=0.7,
            fractal_type="antigravity",
        )

        # Custom rules for Antigravity
        # X -> F-[[X]+X]+F[+FX]-X
        # F -> FF
        genome._production_rules = [
            ("X", "F-[[X]+X]+F[+FX]-X", 1.0),
            ("F", "FF", 1.0),
        ]
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes

        return genome

    @classmethod
    def from_parent(
        cls,
        parent: "PlantGenome",
        mutation_rate: float = 0.15,
        mutation_strength: float = 0.15,
        rng: Optional[random.Random] = None,
    ) -> "PlantGenome":
        """Create offspring genome from a single parent with mutations.

        Args:
            parent: Parent's genome
            mutation_rate: Probability of each trait mutating
            mutation_strength: Magnitude of mutations

        Returns:
            New genome with inherited traits and possible mutations
        """
        rng = rng or random

        def mutate_float(
            val: float, min_val: float, max_val: float
        ) -> float:
            """Apply mutation to a float trait."""
            if rng.random() < mutation_rate:
                val += rng.gauss(0, mutation_strength * (max_val - min_val))
            return max(min_val, min(max_val, val))

        offspring = cls(
            # L-System parameters with mutation
            axiom=parent.axiom,
            angle=mutate_float(parent.angle, 15.0, 45.0),
            length_ratio=mutate_float(parent.length_ratio, 0.5, 0.85),
            branch_probability=mutate_float(parent.branch_probability, 0.6, 1.0),
            curve_factor=mutate_float(parent.curve_factor, 0.0, 0.3),
            # Visual traits
            color_hue=mutate_float(parent.color_hue, 0.2, 0.5),
            color_saturation=mutate_float(parent.color_saturation, 0.4, 1.0),
            stem_thickness=mutate_float(parent.stem_thickness, 0.5, 1.5),
            leaf_density=mutate_float(parent.leaf_density, 0.3, 1.0),
            # Poker traits
            aggression=mutate_float(parent.aggression, 0.0, 1.0),
            bluff_frequency=mutate_float(parent.bluff_frequency, 0.0, 0.5),
            risk_tolerance=mutate_float(parent.risk_tolerance, 0.2, 0.8),
            # Energy traits
            base_energy_rate=mutate_float(parent.base_energy_rate, 0.01, 0.05),
            growth_efficiency=mutate_float(parent.growth_efficiency, 0.5, 1.5),
            nectar_threshold_ratio=mutate_float(parent.nectar_threshold_ratio, 0.6, 0.9),
            fractal_type=parent.fractal_type,
            # Reset fitness
            fitness_score=0.0,
        )

        # Regenerate production rules based on new branch_probability
        offspring._production_rules = offspring._generate_default_rules()

        # Chance to mutate production rules
        if rng.random() < mutation_rate * 2:
            offspring._mutate_production_rules(rng)

        return offspring

    def _mutate_production_rules(self, rng: random.Random) -> None:
        """Apply mutation to production rules."""
        if not self._production_rules:
            return

        # Pick a random rule to modify
        idx = rng.randint(0, len(self._production_rules) - 1)
        input_char, output, prob = self._production_rules[idx]

        # Possible mutations
        mutation_type = rng.choice(["angle_change", "branch_add", "length_change"])

        if mutation_type == "angle_change":
            # Modify angle in rule by tweaking +/- symbols
            if "+" in output or "-" in output:
                # Swap some + and - symbols
                output_list = list(output)
                for i, c in enumerate(output_list):
                    if c in "+-" and rng.random() < 0.3:
                        output_list[i] = "-" if c == "+" else "+"
                output = "".join(output_list)

        elif mutation_type == "branch_add":
            # Add or remove a branch
            if rng.random() < 0.5 and "[" not in output:
                # Add a branch
                insert_pos = rng.randint(1, len(output))
                branch = "[" + rng.choice(["+F", "-F", "F"]) + "]"
                output = output[:insert_pos] + branch + output[insert_pos:]
            elif "[" in output and rng.random() < 0.3:
                # Remove a branch (simplified)
                output = output.replace("[-F]", "", 1)

        elif mutation_type == "length_change":
            # Add or remove F symbols
            if rng.random() < 0.5:
                output = output.replace("F", "FF", 1)
            else:
                output = output.replace("FF", "F", 1)

        # Update the rule
        self._production_rules[idx] = (input_char, output, prob)

    def update_fitness(
        self,
        energy_gained: float = 0.0,
        survived_frames: int = 0,
        nectar_produced: int = 0,
        poker_won: int = 0,
    ) -> None:
        """Update fitness score based on life events.

        Args:
            energy_gained: Energy collected this update
            survived_frames: Frames survived
            nectar_produced: Number of nectar produced
            poker_won: Number of poker games won
        """
        self.fitness_score += (
            energy_gained * 1.0
            + survived_frames * 0.005
            + nectar_produced * 30.0
            + poker_won * 20.0
        )

    def get_color_rgb(self) -> Tuple[int, int, int]:
        """Get RGB color based on genome traits.

        Returns:
            RGB tuple for plant coloring
        """
        # Convert HSL to RGB (simplified)
        h = self.color_hue
        s = self.color_saturation
        l = 0.4  # Lightness

        # HSL to RGB conversion
        if s == 0:
            r = g = b = int(l * 255)
        else:
            def hue_to_rgb(p: float, q: float, t: float) -> float:
                if t < 0:
                    t += 1
                if t > 1:
                    t -= 1
                if t < 1/6:
                    return p + (q - p) * 6 * t
                if t < 1/2:
                    return q
                if t < 2/3:
                    return p + (q - p) * (2/3 - t) * 6
                return p

            q = l * (1 + s) if l < 0.5 else l + s - l * s
            p = 2 * l - q
            r = int(hue_to_rgb(p, q, h + 1/3) * 255)
            g = int(hue_to_rgb(p, q, h) * 255)
            b = int(hue_to_rgb(p, q, h - 1/3) * 255)

        return (r, g, b)

    def to_dict(self) -> Dict:
        """Serialize genome to dictionary for JSON export.

        Returns:
            Dictionary representation of genome
        """
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
        """Deserialize genome from dictionary.

        Args:
            data: Dictionary representation

        Returns:
            PlantGenome instance
        """
        rules = [
            (r["input"], r["output"], r["prob"])
            for r in data.get("production_rules", [])
        ]

        genome = cls(
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
            genome._production_rules = rules
        else:
            genome._production_rules = genome._generate_default_rules()

        return genome
