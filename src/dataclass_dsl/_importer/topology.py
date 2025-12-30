"""
Generic graph algorithms for dependency ordering.

This module provides algorithms that work on abstract dependency graphs
represented as dict[str, set[str]] mappings. Domain packages can use these
for both IR template processing and Python class ordering.

Algorithms:
    - find_sccs_in_graph: Tarjan's algorithm for strongly connected components
    - topological_sort_graph: DAG-based dependency ordering
    - order_scc_by_dependencies: Order nodes within an SCC

The graph representation is:
    graph[node] = {dependencies}

Where each node maps to the set of nodes it depends on.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import TypeVar

__all__ = [
    "find_sccs_in_graph",
    "topological_sort_graph",
    "order_scc_by_dependencies",
]

T = TypeVar("T")


def find_sccs_in_graph(
    graph: Mapping[T, set[T] | list[T] | Iterable[T]],
) -> list[list[T]]:
    """Find strongly connected components using Tarjan's algorithm.

    Identifies groups of nodes that form cycles in the dependency graph.
    Returns SCCs in reverse topological order (dependencies first).

    Args:
        graph: Dependency graph where graph[node] contains nodes that 'node'
            depends on. Can use set, list, or any iterable as values.

    Returns:
        List of SCCs, where each SCC is a list of nodes. Single-node SCCs
        are included (they represent nodes with no cycles). SCCs are in
        reverse topological order, so dependencies appear before dependents.

    Example:
        >>> graph = {"A": {"B"}, "B": {"C"}, "C": {"A"}}  # A -> B -> C -> A cycle
        >>> sccs = find_sccs_in_graph(graph)
        >>> len(sccs)
        1
        >>> sorted(sccs[0])
        ['A', 'B', 'C']

        >>> dag = {"A": {"B", "C"}, "B": {"C"}, "C": set()}
        >>> sccs = find_sccs_in_graph(dag)
        >>> len(sccs)  # Each node is its own SCC (no cycles)
        3
    """
    nodes = set(graph.keys())

    # Normalize graph values to sets
    normalized: dict[T, set[T]] = {}
    for node, deps in graph.items():
        if isinstance(deps, set):
            normalized[node] = deps & nodes
        else:
            normalized[node] = set(deps) & nodes

    index_counter = [0]
    stack: list[T] = []
    lowlinks: dict[T, int] = {}
    index: dict[T, int] = {}
    on_stack: set[T] = set()
    sccs: list[list[T]] = []

    def strongconnect(node: T) -> None:
        index[node] = index_counter[0]
        lowlinks[node] = index_counter[0]
        index_counter[0] += 1
        stack.append(node)
        on_stack.add(node)

        for successor in normalized.get(node, set()):
            if successor not in index:
                strongconnect(successor)
                lowlinks[node] = min(lowlinks[node], lowlinks[successor])
            elif successor in on_stack:
                lowlinks[node] = min(lowlinks[node], index[successor])

        if lowlinks[node] == index[node]:
            scc: list[T] = []
            while True:
                successor = stack.pop()
                on_stack.remove(successor)
                scc.append(successor)
                if successor == node:
                    break
            sccs.append(scc)

    for node in nodes:
        if node not in index:
            strongconnect(node)

    return sccs


def topological_sort_graph(
    graph: dict[T, set[T] | list[T] | Iterable[T]],
) -> list[T]:
    """Sort graph nodes so dependencies come first.

    Performs a topological sort on the dependency graph. If cycles exist,
    nodes within cycles are included but their relative order is arbitrary.

    Args:
        graph: Dependency graph where graph[node] contains nodes that 'node'
            depends on.

    Returns:
        List of nodes in dependency order (dependencies before dependents).

    Example:
        >>> graph = {"A": {"B", "C"}, "B": {"C"}, "C": set()}
        >>> topological_sort_graph(graph)
        ['C', 'B', 'A']
    """
    nodes = set(graph.keys())
    visited: set[T] = set()
    result: list[T] = []

    # Normalize graph values
    normalized: dict[T, set[T]] = {}
    for node, deps in graph.items():
        if isinstance(deps, set):
            normalized[node] = deps & nodes
        else:
            normalized[node] = set(deps) & nodes

    def visit(node: T) -> None:
        if node in visited:
            return
        visited.add(node)

        for dep in normalized.get(node, set()):
            if dep in nodes:
                visit(dep)

        result.append(node)

    for node in nodes:
        visit(node)

    return result


def order_scc_by_dependencies(
    scc: list[T],
    graph: dict[T, set[T] | list[T] | Iterable[T]],
) -> list[T]:
    """Order nodes within an SCC to minimize forward references.

    When nodes form a cycle (SCC with >1 node), this function orders them
    so that nodes with fewer internal dependencies come first, reducing
    the number of forward references needed.

    Note: With two-pass loading in dataclass-dsl, forward references are
    handled automatically. This ordering is an optimization, not a requirement.

    Args:
        scc: List of nodes in a strongly connected component.
        graph: Full dependency graph.

    Returns:
        Nodes ordered to minimize forward references.

    Example:
        >>> # A depends on B, B depends on C, C depends on A
        >>> scc = ["A", "B", "C"]
        >>> graph = {"A": {"B"}, "B": {"C"}, "C": {"A"}}
        >>> ordered = order_scc_by_dependencies(scc, graph)
        >>> # Order determined by internal dependency count
    """
    scc_set = set(scc)

    # Normalize graph values
    normalized: dict[T, set[T]] = {}
    for node, deps in graph.items():
        if isinstance(deps, set):
            normalized[node] = deps & scc_set
        else:
            normalized[node] = set(deps) & scc_set

    # Count internal dependencies for each node
    dep_counts: dict[T, int] = {}
    for node in scc:
        internal_deps = normalized.get(node, set())
        dep_counts[node] = len(internal_deps)

    # Sort by dependency count, then by name for stability
    return sorted(scc, key=lambda n: (dep_counts.get(n, 0), str(n)))
