"""
Dependency ordering utilities for decorated resources.

This module provides functions for analyzing dependencies between decorated
classes and computing topological orderings for creation/deletion.

Uses type annotation introspection combined with runtime AttrRef detection to
compute accurate dependency graphs, supporting both Annotated type hints and
the no-parens pattern.
"""

from __future__ import annotations

from dataclasses import MISSING, fields
from typing import Any

from dataclass_dsl._importer.topology import find_sccs_in_graph
from dataclass_dsl._types import get_dependencies as _get_annotated_dependencies
from dataclass_dsl._utils import DEFAULT_MARKER, is_attr_ref, is_class_ref

__all__ = [
    "get_all_dependencies",
    "topological_sort",
    "get_creation_order",
    "get_deletion_order",
    "detect_cycles",
    "get_dependency_graph",
]


def get_all_dependencies(
    cls: type[Any],
    marker: str = DEFAULT_MARKER,
) -> set[type[Any]]:
    """
    Get all dependencies of a class, from both type annotations and runtime values.

    Combines:
    1. Annotated type hint dependencies from Ref, Attr, RefList, RefDict markers
    2. Runtime AttrRef dependencies from no-parens pattern (Object1.Id)
    3. Runtime class reference dependencies (e.g., parent = Object1)

    Args:
        cls: The wrapper class to analyze.
        marker: The marker attribute name for detecting decorated classes.

    Returns:
        Set of classes this class depends on.

    Example:
        >>> deps = get_all_dependencies(Object3)
        >>> Object2 in deps
        True
    """
    deps: set[type[Any]] = set()

    # Get dependencies from Annotated type hints
    try:
        deps.update(_get_annotated_dependencies(cls))
    except Exception:
        pass  # Ignore errors from type introspection

    # Get runtime dependencies from dataclass fields
    try:
        for field in fields(cls):
            default = field.default
            # Skip MISSING values (no default set)
            if default is MISSING:
                continue
            # Check for AttrRef (no-parens pattern like Object1.Id)
            if is_attr_ref(default):
                deps.add(default.target)
            # Check for class reference (no-parens pattern like Object1)
            elif is_class_ref(default, marker):
                deps.add(default)
            elif isinstance(default, type) and hasattr(default, marker):
                deps.add(default)
    except TypeError:
        # Not a dataclass, skip
        pass

    return deps


def topological_sort(
    classes: list[type[Any]],
    marker: str = DEFAULT_MARKER,
) -> list[type[Any]]:
    """
    Sort classes by dependency order (dependencies first).

    Uses get_all_dependencies() to compute the dependency graph,
    then performs a topological sort so that dependencies appear before
    dependents.

    Args:
        classes: List of wrapper classes to sort.
        marker: The marker attribute name for detecting decorated classes.

    Returns:
        Classes sorted in dependency order (dependencies first).

    Raises:
        ValueError: If circular dependencies exist.

    Example:
        >>> # Given: Object3 depends on Object2 depends on Object1
        >>> sorted_classes = topological_sort([Object3, Object2, Object1])
        >>> sorted_classes
        [Object1, Object2, Object3]
    """
    if not classes:
        return []

    class_set = set(classes)
    sorted_result: list[type[Any]] = []
    remaining = set(classes)

    # Track iterations to detect cycles
    max_iterations = len(classes) * len(classes)
    iterations = 0

    while remaining:
        iterations += 1
        if iterations > max_iterations:
            # Find classes involved in cycle
            cycle_classes = [c.__name__ for c in remaining]
            raise ValueError(f"Circular dependency detected involving: {cycle_classes}")

        # Find classes whose dependencies are all satisfied
        ready = [
            cls
            for cls in remaining
            if get_all_dependencies(cls, marker).issubset(
                set(sorted_result) | (set(classes) - class_set)
            )
        ]

        if not ready:
            # All remaining classes have unsatisfied dependencies
            # This indicates a circular dependency
            cycle_classes = [c.__name__ for c in remaining]
            raise ValueError(f"Circular dependency detected involving: {cycle_classes}")

        for cls in ready:
            sorted_result.append(cls)
            remaining.remove(cls)

    return sorted_result


def get_creation_order(
    classes: list[type[Any]],
    marker: str = DEFAULT_MARKER,
) -> list[type[Any]]:
    """
    Get the order in which resources should be created.

    Dependencies appear before dependents.

    Args:
        classes: List of wrapper classes.
        marker: The marker attribute name for detecting decorated classes.

    Returns:
        Classes in creation order (dependencies first).

    Example:
        >>> order = get_creation_order([Object3, Object2, Object1])
        >>> # Object1 created first, then Object2, then Object3
    """
    return topological_sort(classes, marker)


def get_deletion_order(
    classes: list[type[Any]],
    marker: str = DEFAULT_MARKER,
) -> list[type[Any]]:
    """
    Get the order in which resources should be deleted.

    Dependents appear before dependencies (reverse of creation order).

    Args:
        classes: List of wrapper classes.
        marker: The marker attribute name for detecting decorated classes.

    Returns:
        Classes in deletion order (dependents first).

    Example:
        >>> order = get_deletion_order([Object3, Object2, Object1])
        >>> # Object3 deleted first, then Object2, then Object1
    """
    return list(reversed(topological_sort(classes, marker)))


def detect_cycles(
    classes: list[type[Any]],
    marker: str = DEFAULT_MARKER,
) -> list[tuple[type[Any], ...]]:
    """
    Detect circular dependencies in the given classes.

    Uses Tarjan's algorithm to find strongly connected components.

    Args:
        classes: List of wrapper classes to check.
        marker: The marker attribute name for detecting decorated classes.

    Returns:
        List of tuples, where each tuple contains classes involved in a cycle.
        Empty list if no cycles.

    Example:
        >>> # If A depends on B and B depends on A
        >>> cycles = detect_cycles([A, B])
        >>> cycles
        [(A, B)]
    """
    if not classes:
        return []

    # Build dependency graph
    graph = get_dependency_graph(classes, marker)

    # Use generic SCC algorithm
    sccs = find_sccs_in_graph(graph)

    # Filter to only return cycles (SCCs with more than one element)
    return [tuple(scc) for scc in sccs if len(scc) > 1]


def get_dependency_graph(
    classes: list[type[Any]],
    marker: str = DEFAULT_MARKER,
) -> dict[type[Any], set[type[Any]]]:
    """
    Build a dependency graph for the given classes.

    Args:
        classes: List of wrapper classes.
        marker: The marker attribute name for detecting decorated classes.

    Returns:
        Dict mapping each class to its set of dependencies.

    Example:
        >>> graph = get_dependency_graph([Object3, Object2, Object1])
        >>> graph[Object3]
        {Object2}
        >>> graph[Object2]
        {Object1}
        >>> graph[Object1]
        set()
    """
    class_set = set(classes)
    return {cls: get_all_dependencies(cls, marker) & class_set for cls in classes}
