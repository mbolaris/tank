"""Algorithm registry for mapping behavior classes to source files.

This module provides a mapping from algorithm class names to their source file paths,
enabling AI agents to identify which files to edit when improving underperforming behaviors.
"""

import inspect
import os
from typing import Dict

from core.algorithms import ALL_ALGORITHMS


def get_algorithm_source_map() -> Dict[str, str]:
    """Get a dictionary mapping algorithm class names to their source file paths.

    This mapping is used by AI agents to:
    1. Identify which file contains a specific algorithm
    2. Locate the code to analyze and improve
    3. Generate targeted pull requests for algorithm optimization

    Returns:
        Dictionary mapping algorithm class name to absolute file path
        Example: {"GreedyFoodSeeker": "/path/to/core/algorithms/food_seeking.py"}
    """
    mapping = {}

    for algorithm_class in ALL_ALGORITHMS:
        class_name = algorithm_class.__name__

        # Get the source file for this class
        try:
            source_file = inspect.getfile(algorithm_class)
            # Convert to absolute path
            abs_path = os.path.abspath(source_file)
            mapping[class_name] = abs_path
        except (TypeError, OSError) as e:
            # Handle cases where source file cannot be determined
            mapping[class_name] = f"<unknown: {e}>"

    return mapping


def get_algorithm_id_to_source_map() -> Dict[str, str]:
    """Get a dictionary mapping algorithm IDs to their source file paths.

    Returns:
        Dictionary mapping algorithm_id (e.g., "greedy_food_seeker") to file path
    """
    mapping = {}

    for algorithm_class in ALL_ALGORITHMS:
        # Create instance to get algorithm_id
        try:
            instance = algorithm_class()
            algo_id = instance.algorithm_id

            # Get source file
            source_file = inspect.getfile(algorithm_class)
            abs_path = os.path.abspath(source_file)

            mapping[algo_id] = abs_path
        except (TypeError, OSError, AttributeError) as e:
            # Skip algorithms that can't be instantiated or inspected
            # TypeError: inspect.getfile() fails for built-in classes
            # OSError: File system errors
            # AttributeError: Missing algorithm_id attribute
            continue

    return mapping


def get_algorithm_metadata() -> Dict[str, Dict[str, str]]:
    """Get comprehensive metadata about all algorithms.

    Returns:
        Dictionary with algorithm metadata including:
        - class_name: Python class name
        - algorithm_id: Internal identifier
        - source_file: Absolute path to source file
        - module: Python module path
        - category: Algorithm category (food_seeking, predator_avoidance, etc.)
    """
    metadata = {}

    for algorithm_class in ALL_ALGORITHMS:
        class_name = algorithm_class.__name__

        try:
            # Get instance for algorithm_id
            instance = algorithm_class()
            algo_id = instance.algorithm_id

            # Get source file info
            source_file = inspect.getfile(algorithm_class)
            abs_path = os.path.abspath(source_file)
            module_path = algorithm_class.__module__

            # Determine category from module path using dictionary lookup
            category_keywords = {
                "food_seeking": "food_seeking",
                "predator_avoidance": "predator_avoidance",
                "schooling": "schooling",
                "energy_management": "energy_management",
                "territory": "territory",
                "poker": "poker",
            }
            category = "unknown"
            for keyword, cat_name in category_keywords.items():
                if keyword in module_path:
                    category = cat_name
                    break

            metadata[algo_id] = {
                "class_name": class_name,
                "algorithm_id": algo_id,
                "source_file": abs_path,
                "module": module_path,
                "category": category,
            }
        except (TypeError, OSError, AttributeError) as e:
            # Skip algorithms that can't be instantiated or inspected
            # TypeError: inspect.getfile() fails for built-in classes
            # OSError: File system errors
            # AttributeError: Missing algorithm_id attribute
            continue

    return metadata


if __name__ == "__main__":
    # Test the registry
    print("Algorithm Source Mapping:")
    print("=" * 80)

    source_map = get_algorithm_source_map()
    for class_name, file_path in sorted(source_map.items()):
        print(f"{class_name:30s} -> {file_path}")

    print("\n\nAlgorithm Metadata:")
    print("=" * 80)

    metadata = get_algorithm_metadata()
    for algo_id, info in sorted(metadata.items()):
        print(f"\n{algo_id}:")
        for key, value in info.items():
            print(f"  {key:15s}: {value}")
