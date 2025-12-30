"""
dataclass-dsl: Dataclass runtime machinery for declarative DSLs.

This package provides the runtime machinery to build declarative DSLs using
dataclasses. It enables the "no-parens" pattern where references are expressed
as class names rather than function calls.

The No-Parens Pattern:
    # Traditional (with parentheses)
    parent = get_ref(Object1)
    parent_id = get_attr(Object1, "Id")

    # No-parens (cleaner, declarative)
    parent = Object1
    parent_id = Object1.Id

Type Annotations with Annotated:
    from typing import Annotated
    from dataclass_dsl import Ref, Attr

    @refs
    class Subnet:
        # Type checker sees Network, frameworks see Ref() marker
        network: Annotated[Network, Ref()]
        # Type checker sees str, frameworks see Attr(Gateway, "Id")
        gateway_id: Annotated[str, Attr(Gateway, "Id")]

Example:
    >>> from dataclass_dsl import create_decorator, ResourceRegistry
    >>>
    >>> # Create domain-specific decorator
    >>> registry = ResourceRegistry()
    >>> refs = create_decorator(registry=registry)
    >>>
    >>> @refs
    ... class Object1:
    ...     name: str = "object-1"
    ...
    >>> @refs
    ... class Object2:
    ...     parent = Object1          # No-parens class reference
    ...     parent_id = Object1.Id    # No-parens attribute reference
    ...
    >>> @refs
    ... class Object3:
    ...     dependency = Object2      # Depends on Object2
    ...
    >>> # Get dependencies
    >>> from dataclass_dsl import get_dependencies
    >>> deps = get_dependencies(Object3)
    >>> Object2 in deps
    True
    >>>
    >>> # Topological ordering (dependencies first)
    >>> order = get_creation_order([Object3, Object2, Object1])
    >>> [c.__name__ for c in order]
    ['Object1', 'Object2', 'Object3']
"""

from __future__ import annotations

# Version
__version__ = "0.1.3"

# Runtime marker for attribute references
from dataclass_dsl._attr_ref import AttrRef

# CLI framework utilities
from dataclass_dsl._cli import (
    LintIssue,
    add_common_args,
    create_build_command,
    create_lint_command,
    create_list_command,
    create_validate_command,
    discover_resources,
)

# Codegen utilities
from dataclass_dsl._codegen import (
    PYTHON_KEYWORDS,
    escape_docstring,
    escape_string,
    is_valid_python_identifier,
    sanitize_class_name,
    sanitize_python_name,
    to_pascal_case,
    to_snake_case,
)

# Decorator factory
from dataclass_dsl._decorator import create_decorator

# Importer framework utilities
from dataclass_dsl._importer import (
    find_sccs_in_graph,
    order_scc_by_dependencies,
    topological_sort_graph,
)

# Inspection utilities for dynamic list generation
from dataclass_dsl._inspect import (
    build_reverse_constant_map,
    collect_exports,
    get_module_constants,
    get_module_exports,
    get_package_modules,
)

# IR (Intermediate Representation) base classes
from dataclass_dsl._ir import (
    IROutput,
    IRParameter,
    IRProperty,
    IRResource,
    IRTemplate,
)

# Loader for multi-file packages
from dataclass_dsl._loader import (
    find_class_definitions as find_class_definitions_in_source,
)
from dataclass_dsl._loader import (
    find_refs_in_source,
    setup_resources,
)

# Metaclass for no-parens pattern
from dataclass_dsl._metaclass import RefMeta

# Dependency ordering utilities
from dataclass_dsl._ordering import (
    detect_cycles,
    get_all_dependencies,
    get_creation_order,
    get_deletion_order,
    get_dependency_graph,
    topological_sort,
)

# Base classes for infrastructure resources
from dataclass_dsl._property_type import PropertyType

# Provider ABC for serialization
from dataclass_dsl._provider import Provider

# Registry for tracking decorated classes
from dataclass_dsl._registry import ResourceRegistry
from dataclass_dsl._resource import Resource

# Serialization framework
from dataclass_dsl._serialization import (
    FieldMapper,
    PascalCaseMapper,
    SnakeCaseMapper,
    ValueSerializer,
)

# Stub generation for IDE support
from dataclass_dsl._stubs import (
    StubConfig,
    find_class_definitions,
    find_resource_packages,
    generate_stub_file,
    generate_stubs_for_path,
    regenerate_stubs_for_path,
)

# Template base class
from dataclass_dsl._template import RefTransformer, Template

# Type markers (Annotated-based)
from dataclass_dsl._types import (
    Attr,
    ContextRef,
    Ref,
    RefDict,
    RefInfo,
    RefList,
    get_dependencies,
    get_refs,
)

# Helper functions
from dataclass_dsl._utils import (
    DEFAULT_MARKER,
    apply_metaclass,
    get_ref_target,
    is_attr_ref,
    is_class_ref,
)

__all__ = [
    # Version
    "__version__",
    # Runtime markers
    "AttrRef",
    # Metaclass
    "RefMeta",
    # Decorator factory
    "create_decorator",
    # Registry
    "ResourceRegistry",
    # Ordering utilities
    "get_all_dependencies",
    "topological_sort",
    "get_creation_order",
    "get_deletion_order",
    "detect_cycles",
    "get_dependency_graph",
    # Provider
    "Provider",
    # Base classes
    "Resource",
    "PropertyType",
    # Template
    "Template",
    "RefTransformer",
    # CLI framework
    "discover_resources",
    "add_common_args",
    "create_list_command",
    "create_validate_command",
    "create_build_command",
    "create_lint_command",
    "LintIssue",
    # IR base classes
    "IRProperty",
    "IRParameter",
    "IRResource",
    "IROutput",
    "IRTemplate",
    # Serialization framework
    "FieldMapper",
    "PascalCaseMapper",
    "SnakeCaseMapper",
    "ValueSerializer",
    # Codegen utilities
    "PYTHON_KEYWORDS",
    "to_snake_case",
    "to_pascal_case",
    "sanitize_python_name",
    "sanitize_class_name",
    "is_valid_python_identifier",
    "escape_string",
    "escape_docstring",
    # Importer framework utilities
    "find_sccs_in_graph",
    "topological_sort_graph",
    "order_scc_by_dependencies",
    # Inspection utilities
    "get_package_modules",
    "get_module_constants",
    "get_module_exports",
    "collect_exports",
    "build_reverse_constant_map",
    # Loader
    "setup_resources",
    "find_refs_in_source",
    "find_class_definitions_in_source",
    # Stubs
    "StubConfig",
    "generate_stub_file",
    "find_class_definitions",
    "find_resource_packages",
    "generate_stubs_for_path",
    "regenerate_stubs_for_path",
    # Helpers
    "is_attr_ref",
    "is_class_ref",
    "get_ref_target",
    "apply_metaclass",
    "DEFAULT_MARKER",
    # Type markers (Annotated-based)
    "Ref",
    "Attr",
    "RefList",
    "RefDict",
    "ContextRef",
    "RefInfo",
    "get_refs",
    "get_dependencies",
]
