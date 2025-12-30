"""Module and package inspection utilities for dynamic list generation.

These utilities help domain packages dynamically discover and generate
lists that would otherwise need to be manually maintained.

Example:
    >>> from dataclass_dsl import get_package_modules, build_reverse_constant_map
    >>> # Discover all service modules
    >>> modules = get_package_modules("wetwire_aws.resources")
    >>> # Build reverse constant map
    >>> import wetwire_aws.params as params
    >>> type_map = build_reverse_constant_map(params, str)
"""

from __future__ import annotations

import importlib
import pkgutil
from types import ModuleType
from typing import Any

__all__ = [
    "get_package_modules",
    "get_module_constants",
    "get_module_exports",
    "collect_exports",
    "build_reverse_constant_map",
]


def get_package_modules(package: str | ModuleType) -> list[str]:
    """Find all submodule names in a package (non-recursive).

    Args:
        package: Package name string or module object

    Returns:
        Sorted list of submodule names (e.g., ['ec2', 'iam', 's3'])

    Example:
        >>> get_package_modules("wetwire_aws.resources")
        ['acmpca', 'amplify', 'apigateway', 'autoscaling', ...]
    """
    if isinstance(package, str):
        try:
            package = importlib.import_module(package)
        except ImportError:
            return []

    if not hasattr(package, "__path__"):
        return []

    modules = []
    for _importer, modname, _ispkg in pkgutil.iter_modules(package.__path__):
        # Skip private modules
        if not modname.startswith("_"):
            modules.append(modname)

    return sorted(modules)


def get_module_constants(
    module: ModuleType,
    filter_type: type | None = None,
    exclude_private: bool = True,
) -> dict[str, Any]:
    """Extract constant assignments from a module.

    Constants are identified as UPPERCASE names (by convention).

    Args:
        module: Module to inspect
        filter_type: Only include constants of this type
        exclude_private: Skip names starting with underscore

    Returns:
        Dict mapping constant names to values

    Example:
        >>> import wetwire_aws.params as params
        >>> get_module_constants(params, filter_type=str)
        {'STRING': 'String', 'NUMBER': 'Number', 'VPC_ID': 'AWS::EC2::VPC::Id', ...}
    """
    constants = {}

    for name in dir(module):
        # Skip private names
        if exclude_private and name.startswith("_"):
            continue

        # Only uppercase names (convention for constants)
        if not name.isupper():
            continue

        value = getattr(module, name)

        # Filter by type if specified
        if filter_type is not None and not isinstance(value, filter_type):
            continue

        constants[name] = value

    return constants


def get_module_exports(module: ModuleType) -> list[str]:
    """Get public exports from a module.

    Returns __all__ if defined, otherwise all public names
    (excluding dunder attributes).

    Args:
        module: Module to inspect

    Returns:
        List of exported names

    Example:
        >>> import wetwire_aws.intrinsics as intrinsics
        >>> get_module_exports(intrinsics)
        ['Ref', 'GetAtt', 'Sub', 'Join', ...]
    """
    if hasattr(module, "__all__"):
        return list(module.__all__)

    # Fall back to public names
    return [name for name in dir(module) if not name.startswith("_")]


def collect_exports(*modules: ModuleType) -> list[str]:
    """Collect exports from multiple modules into deduplicated list.

    Args:
        *modules: Modules to collect exports from

    Returns:
        Deduplicated list of all exports (preserves first occurrence order)

    Example:
        >>> from wetwire_aws import intrinsics, params
        >>> collect_exports(intrinsics, params)
        ['Ref', 'GetAtt', ..., 'STRING', 'NUMBER', ...]
    """
    seen = set()
    result = []

    for module in modules:
        for name in get_module_exports(module):
            if name not in seen:
                seen.add(name)
                result.append(name)

    return result


def build_reverse_constant_map(
    module: ModuleType,
    filter_type: type | None = None,
) -> dict[Any, str]:
    """Build value→name mapping from module constants.

    Creates a reverse lookup from constant values to their names.
    Useful for building mappings like PARAMETER_TYPE_MAP automatically.

    Args:
        module: Module containing constant definitions
        filter_type: Only include constants of this type

    Returns:
        Dict mapping values to constant names

    Example:
        >>> # In params.py: STRING = "String", NUMBER = "Number"
        >>> import wetwire_aws.params as params
        >>> build_reverse_constant_map(params, str)
        {'String': 'STRING', 'Number': 'NUMBER', ...}
    """
    constants = get_module_constants(module, filter_type=filter_type)
    return {value: name for name, value in constants.items()}
