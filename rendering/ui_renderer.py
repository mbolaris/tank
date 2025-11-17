"""UI rendering utilities for the fish tank simulator.

This module handles all UI rendering including health bars, stats panels,
and poker notifications.
"""

import pygame
from typing import List, Dict, Any, Optional
from core.constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT,
    POKER_NOTIFICATION_DURATION, POKER_NOTIFICATION_MAX_COUNT,
    POKER_TIE_COLOR, POKER_WIN_COLOR,
    HEALTH_BAR_WIDTH, HEALTH_BAR_HEIGHT,
    HEALTH_CRITICAL_COLOR, HEALTH_LOW_COLOR, HEALTH_GOOD_COLOR
)
from core.behavior_algorithms import get_algorithm_index


class UIRenderer:
    """Renders UI elements for the fish tank simulator.

    This class is responsible for rendering health bars, statistics panels,
    and poker notifications on the screen.

    Attributes:
        screen: Pygame surface to render to
        stats_font: Font for rendering statistics
        frame_count: Current frame count for animations
    """

    def __init__(self, screen: pygame.Surface, stats_font: pygame.font.Font) -> None:
        """Initialize the UI renderer.

        Args:
            screen: Pygame surface to render to
            stats_font: Font for rendering statistics
        """
        self.screen = screen
        self.stats_font = stats_font
        self.frame_count: int = 0

    def set_frame_count(self, frame_count: int) -> None:
        """Update the current frame count for animations.

        Args:
            frame_count: Current frame count
        """
        self.frame_count = frame_count

    def draw_health_bar(self, fish: Any) -> None:
        """Draw health/energy bar above a fish.

        Args:
            fish: The fish to draw health bar for
        """
        # Health bar dimensions
        bar_x = fish.rect.centerx - HEALTH_BAR_WIDTH // 2
        bar_y = fish.rect.top - 8

        # Background (empty bar)
        pygame.draw.rect(self.screen, (60, 60, 60), (bar_x, bar_y, HEALTH_BAR_WIDTH, HEALTH_BAR_HEIGHT))

        # Foreground (filled based on energy)
        energy_ratio = fish.energy / fish.max_energy
        filled_width = int(HEALTH_BAR_WIDTH * energy_ratio)

        # Color based on energy level
        if energy_ratio > 0.6:
            color = HEALTH_GOOD_COLOR
        elif energy_ratio > 0.3:
            color = HEALTH_LOW_COLOR
        else:
            color = HEALTH_CRITICAL_COLOR

        if filled_width > 0:
            pygame.draw.rect(self.screen, color, (bar_x, bar_y, filled_width, HEALTH_BAR_HEIGHT))

        # Display algorithm number if fish has a behavior algorithm
        if fish.genome.behavior_algorithm is not None:
            algo_index = get_algorithm_index(fish.genome.behavior_algorithm)

            if algo_index >= 0:
                # Create a small font for the algorithm number
                small_font = pygame.font.Font(None, 16)
                algo_text = f"#{algo_index}"
                text_surface = small_font.render(algo_text, True, (200, 200, 200))

                # Position text below the health bar, centered
                text_x = fish.rect.centerx - text_surface.get_width() // 2
                text_y = bar_y + HEALTH_BAR_HEIGHT + 1

                self.screen.blit(text_surface, (text_x, text_y))

    def draw_stats_panel(self, ecosystem: Any, time_system: Any, paused: bool) -> None:
        """Draw statistics panel showing ecosystem data.

        Args:
            ecosystem: Ecosystem manager with statistics
            time_system: Time system for day/night cycle
            paused: Whether the simulation is paused
        """
        # Semi-transparent background (larger to fit poker stats)
        panel_surface = pygame.Surface((280, 300))
        panel_surface.set_alpha(200)
        panel_surface.fill((20, 20, 40))
        self.screen.blit(panel_surface, (10, 10))

        # Get stats
        stats = ecosystem.get_summary_stats()
        time_str = time_system.get_time_string()

        # Render text lines
        y_offset = 15
        lines = [
            f"Time: {time_str}",
            f"Population: {stats['total_population']}/{ecosystem.max_population}",
            f"Generation: {stats['current_generation']}",
            f"Births: {stats['total_births']}",
            f"Deaths: {stats['total_deaths']}",
            f"Capacity: {stats['capacity_usage']}",
        ]

        # Add death causes
        if stats['death_causes']:
            lines.append("Death Causes:")
            for cause, count in stats['death_causes'].items():
                lines.append(f"  {cause}: {count}")

        # Add poker stats (always show, even if no games played yet)
        poker = stats.get('poker_stats', {})
        if poker:
            lines.append("")
            lines.append("Poker Stats:")
            if poker.get('total_games', 0) == 0:
                lines.append(("  No poker games yet (need 10+ energy & collision)", (150, 150, 150)))
            else:
                lines.append(f"  Games: {poker['total_games']}")
                lines.append(f"  Wins/Losses/Ties: {poker['total_wins']}/{poker['total_losses']}/{poker['total_ties']}")
                lines.append(f"  Energy Won: {poker['total_energy_won']:.1f}")
                lines.append(f"  Energy Lost: {poker['total_energy_lost']:.1f}")
                lines.append(f"  House Cuts: {poker.get('total_house_cuts', 0):.1f}")
                net_energy = poker['net_energy']
                net_color = (100, 255, 100) if net_energy >= 0 else (255, 100, 100)
                lines.append((f"  Net Energy: {net_energy:+.1f}", net_color))
                lines.append(f"  Best Hand: {poker['best_hand_name']}")

        for line in lines:
            # Check if line is a tuple (text, color)
            if isinstance(line, tuple):
                text, color = line
                text_surface = self.stats_font.render(text, True, color)
            else:
                text_surface = self.stats_font.render(line, True, (220, 220, 255))
            self.screen.blit(text_surface, (20, y_offset))
            y_offset += 22

        # Show pause indicator
        if paused:
            pause_text = self.stats_font.render("PAUSED", True, (255, 200, 100))
            self.screen.blit(pause_text, (SCREEN_WIDTH // 2 - 40, 10))

    def draw_poker_notifications(self, poker_notifications: List[Dict[str, Any]]) -> None:
        """Draw poker notifications on the screen.

        Args:
            poker_notifications: List of poker notification dictionaries
        """
        # Draw notifications in the bottom-right corner
        y_offset = SCREEN_HEIGHT - 30
        for notif in reversed(poker_notifications):  # Newest at bottom
            # Calculate fade based on age
            age = self.frame_count - notif['frame']
            fade_start = notif['duration'] - 60  # Start fading 2 seconds before expiry
            if age > fade_start:
                alpha = int(255 * (notif['duration'] - age) / 60)
            else:
                alpha = 255

            # Render text
            text_surface = self.stats_font.render(notif['message'], True, notif['color'])

            # Create surface with alpha
            notification_surface = pygame.Surface((text_surface.get_width() + 20, text_surface.get_height() + 10))
            notification_surface.set_alpha(min(alpha, 220))
            notification_surface.fill((20, 20, 40))

            # Position in bottom-right
            x_pos = SCREEN_WIDTH - notification_surface.get_width() - 10
            y_pos = y_offset - notification_surface.get_height()

            # Draw background and text
            self.screen.blit(notification_surface, (x_pos, y_pos))
            self.screen.blit(text_surface, (x_pos + 10, y_pos + 5))

            y_offset = y_pos - 5  # Move up for next notification
