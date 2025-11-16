#!/usr/bin/env python3
"""Generate diverse and interesting food graphics for the tank simulation."""

import pygame
import random
import math
import os

# Initialize pygame
pygame.init()

def create_algae_flake(size=24):
    """Create a green algae flake (high in plant nutrients)."""
    surface = pygame.Surface((size, size), pygame.SRCALPHA)

    # Create irregular organic blob
    center_x, center_y = size // 2, size // 2
    points = []
    num_points = 8

    for i in range(num_points):
        angle = (i / num_points) * 2 * math.pi
        radius = random.uniform(size * 0.3, size * 0.45)
        x = center_x + radius * math.cos(angle)
        y = center_y + radius * math.sin(angle)
        points.append((x, y))

    # Draw filled polygon (dark green)
    pygame.draw.polygon(surface, (34, 139, 34, 230), points)
    # Outline (lighter green)
    pygame.draw.polygon(surface, (50, 205, 50, 255), points, 1)

    # Add some texture dots
    for _ in range(5):
        dot_x = random.randint(size // 4, 3 * size // 4)
        dot_y = random.randint(size // 4, 3 * size // 4)
        pygame.draw.circle(surface, (20, 100, 20, 180), (dot_x, dot_y), 1)

    return surface

def create_protein_flake(size=24):
    """Create a red/pink protein flake."""
    surface = pygame.Surface((size, size), pygame.SRCALPHA)

    # Create chunky irregular shape
    center_x, center_y = size // 2, size // 2
    points = []
    num_points = 6

    for i in range(num_points):
        angle = (i / num_points) * 2 * math.pi
        radius = random.uniform(size * 0.35, size * 0.48)
        x = center_x + radius * math.cos(angle)
        y = center_y + radius * math.sin(angle)
        points.append((x, y))

    # Draw filled polygon (red/pink)
    pygame.draw.polygon(surface, (220, 20, 60, 240), points)
    # Outline (darker red)
    pygame.draw.polygon(surface, (139, 0, 0, 255), points, 1)

    # Add highlight
    highlight_x = center_x - 3
    highlight_y = center_y - 3
    pygame.draw.circle(surface, (255, 100, 100, 200), (highlight_x, highlight_y), 2)

    return surface

def create_vitamin_flake(size=24):
    """Create an orange vitamin flake."""
    surface = pygame.Surface((size, size), pygame.SRCALPHA)

    # Create star-like shape
    center_x, center_y = size // 2, size // 2
    points = []
    num_points = 10

    for i in range(num_points):
        angle = (i / num_points) * 2 * math.pi
        if i % 2 == 0:
            radius = size * 0.45
        else:
            radius = size * 0.25
        x = center_x + radius * math.cos(angle - math.pi / 2)
        y = center_y + radius * math.sin(angle - math.pi / 2)
        points.append((x, y))

    # Draw filled polygon (orange)
    pygame.draw.polygon(surface, (255, 140, 0, 235), points)
    # Outline (darker orange)
    pygame.draw.polygon(surface, (255, 69, 0, 255), points, 1)

    # Add sparkle
    pygame.draw.line(surface, (255, 215, 0, 255), (center_x-4, center_y), (center_x+4, center_y), 1)
    pygame.draw.line(surface, (255, 215, 0, 255), (center_x, center_y-4), (center_x, center_y+4), 1)

    return surface

def create_energy_flake(size=24):
    """Create a yellow energy/carb flake."""
    surface = pygame.Surface((size, size), pygame.SRCALPHA)

    # Create rounded hexagon
    center_x, center_y = size // 2, size // 2
    points = []
    num_points = 6

    for i in range(num_points):
        angle = (i / num_points) * 2 * math.pi
        radius = size * 0.42
        x = center_x + radius * math.cos(angle)
        y = center_y + radius * math.sin(angle)
        points.append((x, y))

    # Draw filled polygon (yellow)
    pygame.draw.polygon(surface, (255, 215, 0, 230), points)
    # Outline (golden)
    pygame.draw.polygon(surface, (218, 165, 32, 255), points, 1)

    # Add inner detail
    inner_points = []
    for i in range(num_points):
        angle = (i / num_points) * 2 * math.pi
        radius = size * 0.25
        x = center_x + radius * math.cos(angle)
        y = center_y + radius * math.sin(angle)
        inner_points.append((x, y))
    pygame.draw.polygon(surface, (184, 134, 11, 200), inner_points, 1)

    return surface

def create_rare_flake(size=24):
    """Create a rare multi-nutrient flake (rainbow/iridescent)."""
    surface = pygame.Surface((size, size), pygame.SRCALPHA)

    # Create diamond shape
    center_x, center_y = size // 2, size // 2
    points = [
        (center_x, center_y - size * 0.45),  # top
        (center_x + size * 0.45, center_y),  # right
        (center_x, center_y + size * 0.45),  # bottom
        (center_x - size * 0.45, center_y),  # left
    ]

    # Draw filled polygon (purple)
    pygame.draw.polygon(surface, (138, 43, 226, 240), points)
    # Outline (indigo)
    pygame.draw.polygon(surface, (75, 0, 130, 255), points, 1)

    # Add colorful highlights
    pygame.draw.circle(surface, (255, 20, 147, 200), (center_x, center_y-3), 3)
    pygame.draw.circle(surface, (0, 191, 255, 200), (int(center_x+3.5), int(center_y+2.5)), 2)

    return surface

def main():
    """Generate all food graphics with variations."""

    # Ensure images directory exists
    os.makedirs('images', exist_ok=True)

    # Create 2 variations of each food type
    food_types = [
        ('algae', create_algae_flake),
        ('protein', create_protein_flake),
        ('vitamin', create_vitamin_flake),
        ('energy', create_energy_flake),
        ('rare', create_rare_flake),
    ]

    for food_name, generator_func in food_types:
        # Create 2 variations for animation
        for i in range(1, 3):
            # Set random seed for consistent but varied results
            random.seed(i * 100)
            surface = generator_func(24)

            # Rotate second frame slightly for animation effect
            if i == 2:
                angle = random.randint(15, 30)
                # Create rotated surface
                rotated = pygame.transform.rotate(surface, angle)
                # Crop back to original size
                rect = rotated.get_rect()
                surface = pygame.Surface((24, 24), pygame.SRCALPHA)
                surface.blit(rotated, ((24 - rect.width) // 2, (24 - rect.height) // 2))

            filename = f'images/food_{food_name}{i}.png'
            pygame.image.save(surface, filename)
            print(f"Created {filename}")

    pygame.quit()

if __name__ == '__main__':
    main()
