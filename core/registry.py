"""Algorithm introspection utilities.

This module provides metadata and source file location utilities for algorithms.
Used by AI tooling and stats exporters to introspect algorithm definitions.

For runtime algorithm operations (crossover, mutation, instantiation), see:
    core.algorithms.registry
"""
import inspect
import os
import pkgutil
from importlib import import_module
from typing import Dict, Iterable, List, Set, Type

from core import algorithms
from core.algorithms.base import BehaviorAlgorithm, BehaviorStrategyBase


def _iter_algorithm_modules() -> Iterable[str]:
    """Yield fully qualified algorithm module paths within core.algorithms."""
    for module_info in pkgutil.walk_packages(algorithms.__path__, prefix="core.algorithms."):
        stem = module_info.name.rsplit(".", 1)[-1]
        if stem.startswith("__") or stem in {"base", "BEHAVIOR_TEMPLATE"}:
            continue
        yield module_info.name


def _discover_algorithms() -> List[Type[BehaviorStrategyBase]]:
    """Dynamically import and collect behavior strategy classes."""

    discovered: List[Type[BehaviorStrategyBase]] = []
    seen: Set[Type[BehaviorStrategyBase]] = set()

    for module_name in _iter_algorithm_modules():
        module = import_module(module_name)
        for _, obj in inspect.getmembers(module, inspect.isclass):
            if not issubclass(obj, BehaviorStrategyBase) or obj in {
                BehaviorStrategyBase,
                BehaviorAlgorithm,
            }:
                continue
            if obj in seen:
                continue
            seen.add(obj)
            discovered.append(obj)

    return discovered


ALL_ALGORITHMS: List[Type[BehaviorStrategyBase]] = _discover_algorithms()


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
        except (TypeError, OSError, AttributeError):
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
        except (TypeError, OSError, AttributeError):
            # Skip algorithms that can't be instantiated or inspected
            # TypeError: inspect.getfile() fails for built-in classes
            # OSError: File system errors
            # AttributeError: Missing algorithm_id attribute
            continue

    return metadata

