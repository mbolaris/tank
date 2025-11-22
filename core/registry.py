"""Algorithm registry utilities.

This module discovers behavior algorithms dynamically and exposes helpers for
introspecting where they live on disk. It now includes a registry class that
automatically loads any new algorithms without manual imports.
"""
import importlib
import inspect
import os
import pkgutil
from importlib import import_module
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Type

from core import algorithms
from core.algorithms.base import BehaviorAlgorithm, BehaviorStrategy


class AlgorithmRegistry:
    """Dynamic registry for behavior strategies."""

    _strategies: Dict[str, Type[BehaviorStrategy]] = {}

    @classmethod
    def load_algorithms(cls) -> None:
        """Scan ``core.algorithms`` for strategies and register them by name."""

        package_path = algorithms.__path__

        for _, name, _ in pkgutil.iter_modules(package_path):
            module = importlib.import_module(f"core.algorithms.{name}")

            for attribute_name in dir(module):
                attribute = getattr(module, attribute_name)

                if (
                    inspect.isclass(attribute)
                    and issubclass(attribute, BehaviorStrategy)
                    and attribute is not BehaviorStrategy
                ):
                    key = attribute.name() if hasattr(attribute, "name") else name
                    cls._strategies[key] = attribute

    @classmethod
    def get(cls, name: str) -> Optional[Type[BehaviorStrategy]]:
        """Retrieve a registered behavior strategy class by name."""

        return cls._strategies.get(name)


# Populate the registry on import so callers can immediately request strategies.
AlgorithmRegistry.load_algorithms()


def _iter_algorithm_modules() -> Iterable[str]:
    """Yield fully qualified algorithm module paths within core.algorithms."""

    algorithms_dir = Path(__file__).resolve().parent / "algorithms"
    for module_path in sorted(algorithms_dir.glob("*.py")):
        stem = module_path.stem
        if stem.startswith("__") or stem in {"base", "BEHAVIOR_TEMPLATE"}:
            continue
        yield f"core.algorithms.{stem}"


def _discover_algorithms() -> List[Type[BehaviorStrategy]]:
    """Dynamically import and collect behavior strategy classes."""

    discovered: List[Type[BehaviorStrategy]] = []
    seen: Set[Type[BehaviorStrategy]] = set()

    for module_name in _iter_algorithm_modules():
        module = import_module(module_name)
        for _, obj in inspect.getmembers(module, inspect.isclass):
            if not issubclass(obj, BehaviorStrategy) or obj in {
                BehaviorStrategy,
                BehaviorAlgorithm,
            }:
                continue
            if obj in seen:
                continue
            seen.add(obj)
            discovered.append(obj)

    return discovered


ALL_ALGORITHMS: List[Type[BehaviorStrategy]] = _discover_algorithms()


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



