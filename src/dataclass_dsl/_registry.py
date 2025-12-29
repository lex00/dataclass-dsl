"""
Global registry for decorated classes.

This module provides ResourceRegistry, which enables auto-registration
of decorated classes for multi-file template organization and type-based
queries. Works with the `from . import *` pattern via setup_resources().

Example:
    # objects/object1.py
    @refs
    class Object1:
        name: str = "object-1"
        # Automatically registered!

    # main.py
    from dataclass_dsl import ResourceRegistry

    registry = ResourceRegistry()
    # ... decorator registers classes here ...

    # Get all registered objects
    all_objects = registry.get_all()
"""

from __future__ import annotations

from collections.abc import Iterator
from threading import Lock
from typing import Any

__all__ = ["ResourceRegistry"]


class ResourceRegistry:
    """
    Thread-safe registry for decorated classes.

    Resources auto-register when decorated, enabling:
    - Multi-file template organization with `from . import *`
    - Type-based queries
    - Automatic template building via Template.from_registry()

    This registry is designed to be used as either:
    1. A global singleton for simple use cases
    2. Separate instances for isolated registration (e.g., testing)

    Attributes:
        _resources: Dict mapping class name to class.
        _by_type: Dict mapping resource type to list of classes.
        _lock: Threading lock for thread-safe operations.

    Example:
        >>> registry = ResourceRegistry()
        >>> @refs(registry=registry)
        ... class Object1:
        ...     name: str = "object-1"
        ...
        >>> "Object1" in registry
        True
        >>> registry.get_by_name("Object1")
        <class 'Object1'>
    """

    def __init__(self) -> None:
        """Initialize an empty registry."""
        self._resources: dict[str, type[Any]] = {}  # class_name -> class
        self._by_type: dict[
            type[Any] | str, list[type[Any]]
        ] = {}  # resource_type -> [classes]
        self._lock = Lock()

    def register(
        self,
        wrapper_cls: type[Any],
        resource_type: type[Any] | str | None = None,
    ) -> None:
        """
        Register a wrapper class.

        Args:
            wrapper_cls: The decorated class to register.
            resource_type: The underlying resource type (optional).
                If not provided, the class is registered by name only.

        Example:
            >>> registry = ResourceRegistry()
            >>> registry.register(Object1)
            >>> "Object1" in registry
            True
        """
        with self._lock:
            name = wrapper_cls.__name__
            self._resources[name] = wrapper_cls

            if resource_type is not None:
                if resource_type not in self._by_type:
                    self._by_type[resource_type] = []
                self._by_type[resource_type].append(wrapper_cls)

    def get_all(self, scope_package: str | None = None) -> list[type[Any]]:
        """
        Get all registered wrapper classes, optionally filtered by package.

        Args:
            scope_package: If provided, only return resources from modules
                that start with this package name.

        Returns:
            List of registered wrapper classes.

        Example:
            >>> registry.get_all()  # All objects
            [<class 'Object1'>, <class 'Object2'>]
            >>> registry.get_all("myproject.objects")  # Only from myproject.objects.*
            [<class 'Object1'>]
        """
        with self._lock:
            resources = list(self._resources.values())

        if scope_package:
            resources = [r for r in resources if r.__module__.startswith(scope_package)]
        return resources

    def get_by_type(self, resource_type: type[Any] | str) -> list[type[Any]]:
        """
        Get wrapper classes by their underlying resource type.

        Args:
            resource_type: The resource type class or string identifier.

        Returns:
            List of wrapper classes that wrap the specified resource type.

        Example:
            >>> objects = registry.get_by_type("MyType")
            >>> len(objects)
            1
        """
        with self._lock:
            return list(self._by_type.get(resource_type, []))

    def get_by_name(self, name: str) -> type[Any] | None:
        """
        Get a wrapper class by its class name.

        Args:
            name: The class name (e.g., "Object1").

        Returns:
            The wrapper class, or None if not found.

        Example:
            >>> registry.get_by_name("Object1")
            <class 'Object1'>
            >>> registry.get_by_name("NonExistent")
            None
        """
        with self._lock:
            return self._resources.get(name)

    def clear(self) -> None:
        """
        Clear the registry.

        Useful for testing to ensure isolation between tests.

        Example:
            >>> registry.clear()
            >>> len(registry)
            0
        """
        with self._lock:
            self._resources.clear()
            self._by_type.clear()

    def __len__(self) -> int:
        """Return the number of registered resources."""
        with self._lock:
            return len(self._resources)

    def __contains__(self, item: str | type) -> bool:
        """Check if a resource is registered by name or class."""
        with self._lock:
            if isinstance(item, str):
                return item in self._resources
            elif isinstance(item, type):
                return item in self._resources.values()
            return False

    def __iter__(self) -> Iterator[type[Any]]:
        """Iterate over registered classes."""
        with self._lock:
            return iter(list(self._resources.values()))

    def __repr__(self) -> str:
        """Return a string representation of the registry."""
        with self._lock:
            count = len(self._resources)
        return f"ResourceRegistry({count} resources)"
