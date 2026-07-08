"""Algorithm introspection utilities.

This module provides metadata and source file location utilities for algorithms.
Used by AI tooling and stats exporters to introspect algorithm definitions.

Discovery here walks the ``core.algorithms`` package and collects every
``BehaviorStrategyBase`` subclass it finds. That is a *different* (broader) set
than the canonical, hand-curated ``ALL_ALGORITHMS`` list in
``core.algorithms.registry``, which defines the stable algorithm-id space used
by genomes and stats. Introspection results are for tooling and reporting only
and must never be used for algorithm-id assignment (see ADR-014).

For runtime algorithm operations (crossover, mutation, instantiation), see:
    core.algorithms.registry
"""

import inspect
import os
import pkgutil
import random
from collections.abc import Callable, Iterable
from importlib import import_module
from typing import cast

import core.algorithms as algorithms
from core.algorithms.base import BehaviorAlgorithm, BehaviorStrategyBase
from core.util.rng import MissingRNGError


def _instantiate_for_metadata(algorithm_class: type[BehaviorStrategyBase]) -> BehaviorStrategyBase:
    """Instantiate an algorithm class just to read its metadata.

    Classes that randomize initial parameters refuse a bare constructor call
    (``MissingRNGError``); a throwaway seeded RNG is fine here because the
    instance is only inspected for its ``algorithm_id``, never simulated.
    """
    try:
        return algorithm_class()
    except MissingRNGError:
        # Subclasses accept rng=...; the base class signature does not declare it.
        ctor = cast(Callable[..., BehaviorStrategyBase], algorithm_class)
        return ctor(rng=random.Random(0))


def _iter_algorithm_modules() -> Iterable[str]:
    """Yield fully qualified algorithm module paths within core.algorithms."""
    for module_info in pkgutil.walk_packages(algorithms.__path__, prefix="core.algorithms."):
        stem = module_info.name.rsplit(".", 1)[-1]
        if stem.startswith("__") or stem in {"base", "BEHAVIOR_TEMPLATE", "introspection"}:
            continue
        yield module_info.name


def discover_algorithm_classes() -> list[type[BehaviorStrategyBase]]:
    """Dynamically import and collect behavior strategy classes.

    Returns every ``BehaviorStrategyBase`` subclass defined under
    ``core.algorithms``, in module-walk order. This is a tooling view of the
    package contents, not the canonical registry ordering.
    """

    discovered: list[type[BehaviorStrategyBase]] = []
    seen: set[type[BehaviorStrategyBase]] = set()

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


def get_algorithm_metadata() -> dict[str, dict[str, str]]:
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

    for algorithm_class in discover_algorithm_classes():
        class_name = algorithm_class.__name__

        try:
            # Get instance for algorithm_id
            instance = _instantiate_for_metadata(algorithm_class)
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
