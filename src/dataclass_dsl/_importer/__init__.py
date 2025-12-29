"""
Importer framework utilities for parsing and generating code from templates.

This module provides generic algorithms and utilities that domain packages
can use when implementing template importers/deserializers.

Graph Algorithms:
    - find_sccs_in_graph: Find strongly connected components (Tarjan's algorithm)
    - topological_sort_graph: Sort nodes in dependency order
    - order_scc_by_dependencies: Order nodes within an SCC to minimize forward refs

Example:
    >>> from dataclass_dsl._importer import (
    ...     find_sccs_in_graph,
    ...     topological_sort_graph,
    ... )
    >>>
    >>> # Build a dependency graph
    >>> graph = {
    ...     "A": {"B", "C"},
    ...     "B": {"C"},
    ...     "C": set(),
    ... }
    >>>
    >>> # Sort in dependency order
    >>> sorted_nodes = topological_sort_graph(graph)
    >>> sorted_nodes
    ['C', 'B', 'A']
    >>>
    >>> # Find cycles
    >>> cyclic_graph = {"A": {"B"}, "B": {"A"}}
    >>> sccs = find_sccs_in_graph(cyclic_graph)
    >>> any(len(scc) > 1 for scc in sccs)
    True
"""

from dataclass_dsl._importer.topology import (
    find_sccs_in_graph,
    order_scc_by_dependencies,
    topological_sort_graph,
)

__all__ = [
    "find_sccs_in_graph",
    "topological_sort_graph",
    "order_scc_by_dependencies",
]
