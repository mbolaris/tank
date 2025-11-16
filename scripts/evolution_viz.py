"""Evolution visualization for tracking genetic trait changes.

This module provides real-time visualization of how genetic traits
evolve across generations.
"""

import pygame
from typing import List, Dict, Tuple, Optional
from collections import deque, defaultdict


class EvolutionVisualizer:
    """Visualizes trait evolution over time with simple line graphs.

    Attributes:
        history_length: Number of data points to keep
        trait_history: Dict of trait name -> deque of (generation, average_value) tuples
        generation_counter: Tracks data points added
    """

    def __init__(self, history_length: int = 100):
        """Initialize the evolution visualizer.

        Args:
            history_length: Maximum number of data points to store per trait
        """
        self.history_length = history_length
        self.trait_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=history_length))
        self.generation_counter = 0

    def record_generation(self, fish_list: List['agents.Fish']) -> None:
        """Record trait averages for current generation.

        Args:
            fish_list: List of all living fish
        """
        if not fish_list:
            return

        self.generation_counter += 1

        # Calculate averages for each trait
        traits = {
            'speed': [],
            'size': [],
            'metabolism': [],
            'energy': [],
            'fertility': [],
        }

        for fish in fish_list:
            if hasattr(fish, 'genome'):
                traits['speed'].append(fish.genome.speed_modifier)
                traits['size'].append(fish.genome.size_modifier)
                traits['metabolism'].append(fish.genome.metabolism_rate)
                traits['energy'].append(fish.genome.max_energy)
                traits['fertility'].append(fish.genome.fertility)

        # Store averages
        for trait_name, values in traits.items():
            if values:
                avg_value = sum(values) / len(values)
                self.trait_history[trait_name].append((self.generation_counter, avg_value))

    def draw_graphs(self, screen: pygame.Surface, x: int, y: int,
                    width: int, height: int, font: pygame.font.Font) -> None:
        """Draw evolution graphs on screen.

        Args:
            screen: Pygame surface to draw on
            x: X position of graph panel
            y: Y position of graph panel
            width: Width of graph panel
            height: Height of graph panel
            font: Font for labels
        """
        # Background
        panel = pygame.Surface((width, height))
        panel.set_alpha(200)
        panel.fill((20, 20, 40))
        screen.blit(panel, (x, y))

        # Title
        title = font.render("Trait Evolution", True, (220, 220, 255))
        screen.blit(title, (x + 10, y + 5))

        # Draw mini graphs for each trait
        graph_height = 35
        graph_spacing = 5
        graph_y_start = y + 30

        traits_to_show = ['speed', 'size', 'metabolism', 'energy', 'fertility']
        colors = [
            (100, 200, 255),  # Blue for speed
            (255, 200, 100),  # Orange for size
            (200, 100, 255),  # Purple for metabolism
            (100, 255, 100),  # Green for energy
            (255, 100, 200),  # Pink for fertility
        ]

        for i, (trait_name, color) in enumerate(zip(traits_to_show, colors)):
            graph_y = graph_y_start + i * (graph_height + graph_spacing)

            # Draw trait label
            label = font.render(trait_name.capitalize()[:5], True, color)
            screen.blit(label, (x + 5, graph_y))

            # Draw mini graph
            self._draw_mini_graph(
                screen,
                x + 60,
                graph_y,
                width - 70,
                graph_height,
                trait_name,
                color
            )

    def _draw_mini_graph(self, screen: pygame.Surface, x: int, y: int,
                         width: int, height: int, trait_name: str, color: Tuple[int, int, int]) -> None:
        """Draw a single mini line graph.

        Args:
            screen: Pygame surface
            x: Graph X position
            y: Graph Y position
            width: Graph width
            height: Graph height
            trait_name: Name of trait to graph
            color: RGB color for the line
        """
        history = self.trait_history.get(trait_name, deque())

        if len(history) < 2:
            return  # Need at least 2 points to draw

        # Background box
        pygame.draw.rect(screen, (10, 10, 20), (x, y, width, height))
        pygame.draw.rect(screen, (50, 50, 70), (x, y, width, height), 1)  # Border

        # Find min/max for scaling
        values = [val for _, val in history]
        min_val = min(values)
        max_val = max(values)
        val_range = max_val - min_val if max_val > min_val else 1.0

        # Draw line
        points = []
        for i, (gen, value) in enumerate(history):
            # X position based on history index
            point_x = x + int((i / (len(history) - 1)) * (width - 2)) + 1

            # Y position based on value (inverted because Y grows downward)
            normalized = (value - min_val) / val_range if val_range > 0 else 0.5
            point_y = y + height - int(normalized * (height - 4)) - 2

            points.append((point_x, point_y))

        if len(points) >= 2:
            pygame.draw.lines(screen, color, False, points, 2)

        # Draw current value
        current_val = values[-1]
        val_text = f"{current_val:.2f}"
        text = pygame.font.Font(None, 16).render(val_text, True, color)
        screen.blit(text, (x + width - 35, y + 2))


class SpeciesTracker:
    """Tracks which AI strategy is performing better.

    Attributes:
        neural_births: Births from neural AI fish
        neural_deaths: Deaths from neural AI fish
        traditional_births: Births from traditional AI fish
        traditional_deaths: Deaths from traditional AI fish
    """

    def __init__(self):
        """Initialize species tracker."""
        self.neural_births = 0
        self.neural_deaths = 0
        self.traditional_births = 0
        self.traditional_deaths = 0

    def record_birth(self, has_neural_brain: bool) -> None:
        """Record a birth.

        Args:
            has_neural_brain: Whether the fish has a neural network brain
        """
        if has_neural_brain:
            self.neural_births += 1
        else:
            self.traditional_births += 1

    def record_death(self, has_neural_brain: bool) -> None:
        """Record a death.

        Args:
            has_neural_brain: Whether the fish has a neural network brain
        """
        if has_neural_brain:
            self.neural_deaths += 1
        else:
            self.traditional_deaths += 1

    def get_survival_rates(self) -> Tuple[float, float]:
        """Get survival rates for each species.

        Returns:
            Tuple of (neural_survival_rate, traditional_survival_rate)
        """
        neural_total = self.neural_births
        neural_survived = neural_total - self.neural_deaths
        neural_rate = neural_survived / neural_total if neural_total > 0 else 0.0

        trad_total = self.traditional_births
        trad_survived = trad_total - self.traditional_deaths
        trad_rate = trad_survived / trad_total if trad_total > 0 else 0.0

        return neural_rate, trad_rate

    def draw_comparison(self, screen: pygame.Surface, x: int, y: int,
                        width: int, height: int, font: pygame.font.Font) -> None:
        """Draw species comparison panel.

        Args:
            screen: Pygame surface
            x: X position
            y: Y position
            width: Panel width
            height: Panel height
            font: Font for text
        """
        # Background
        panel = pygame.Surface((width, height))
        panel.set_alpha(200)
        panel.fill((20, 20, 40))
        screen.blit(panel, (x, y))

        # Title
        title = font.render("AI Performance", True, (220, 220, 255))
        screen.blit(title, (x + 10, y + 5))

        # Neural AI stats
        y_offset = y + 30
        neural_text = f"Neural AI: {self.neural_births - self.neural_deaths}/{self.neural_births}"
        neural_color = (100, 200, 255)
        text = font.render(neural_text, True, neural_color)
        screen.blit(text, (x + 10, y_offset))

        # Traditional AI stats
        y_offset += 25
        trad_text = f"Rule-based: {self.traditional_births - self.traditional_deaths}/{self.traditional_births}"
        trad_color = (255, 200, 100)
        text = font.render(trad_text, True, trad_color)
        screen.blit(text, (x + 10, y_offset))

        # Winner indicator
        neural_rate, trad_rate = self.get_survival_rates()
        if self.neural_births > 0 and self.traditional_births > 0:
            y_offset += 30
            if neural_rate > trad_rate:
                winner_text = "Neural AI leading!"
                winner_color = neural_color
            elif trad_rate > neural_rate:
                winner_text = "Rule-based leading!"
                winner_color = trad_color
            else:
                winner_text = "Tied!"
                winner_color = (200, 200, 200)

            text = font.render(winner_text, True, winner_color)
            screen.blit(text, (x + 10, y_offset))
