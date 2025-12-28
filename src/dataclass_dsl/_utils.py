"""
Helper utilities for dataclass-dsl.

This module provides helper functions for working with references
in the no-parens pattern:
- is_attr_ref: Check if an object is an AttrRef marker
- is_class_ref: Check if an object is a decorated class reference
- get_ref_target: Extract the target class from a reference
- apply_metaclass: Apply a metaclass to an existing class
"""

from __future__ import annotations

from typing import Any, TypeVar

from dataclass_dsl._attr_ref import AttrRef

__all__ = [
    "is_attr_ref",
    "is_class_ref",
    "get_ref_target",
    "apply_metaclass",
]

T = TypeVar("T")

# Default marker attribute name
DEFAULT_MARKER = "_refs_marker"


def is_attr_ref(obj: Any) -> bool:
    """
    Check if an object is an AttrRef marker (no-parens attribute reference).

    Args:
        obj: The object to check.

    Returns:
        True if obj is an AttrRef instance, False otherwise.

    Example:
        >>> @refs
        ... class Object1:
        ...     name: str = "object-1"
        ...
        >>> is_attr_ref(Object1.Id)
        True
        >>> is_attr_ref(Object1)
        False
    """
    return isinstance(obj, AttrRef)


def is_class_ref(obj: Any, marker: str = DEFAULT_MARKER) -> bool:
    """
    Check if an object is a decorated class reference (no-parens class reference).

    A class is considered a reference if it has the specified marker attribute
    set by the decorator.

    Args:
        obj: The object to check.
        marker: The marker attribute name to look for.
            Defaults to "_refs_marker".

    Returns:
        True if obj is a type with the marker attribute, False otherwise.

    Example:
        >>> @refs
        ... class Object1:
        ...     name: str = "object-1"
        ...
        >>> is_class_ref(Object1)
        True
        >>> is_class_ref(str)
        False
    """
    return isinstance(obj, type) and hasattr(obj, marker)


def get_ref_target(obj: Any) -> type | None:
    """
    Extract the target class from an AttrRef or class reference.

    Args:
        obj: An AttrRef or a class reference.

    Returns:
        The target class if obj is a reference, None otherwise.

    Example:
        >>> @refs
        ... class Object1:
        ...     name: str = "object-1"
        ...
        >>> get_ref_target(Object1.Id)
        <class 'Object1'>
        >>> get_ref_target(Object1)
        <class 'Object1'>
        >>> get_ref_target("not a ref")
        None
    """
    if isinstance(obj, AttrRef):
        return obj.target
    if isinstance(obj, type):
        return obj
    return None


def apply_metaclass(cls: type[T], metaclass: type) -> type[T]:
    """
    Apply a metaclass to an existing class.

    This creates a new class with the same name, bases, and attributes,
    but with the specified metaclass. Useful for adding metaclass behavior
    to a class after @dataclass has been applied.

    Args:
        cls: The class to transform.
        metaclass: The metaclass to apply.

    Returns:
        A new class with the metaclass applied.

    Example:
        >>> from dataclasses import dataclass
        >>> @dataclass
        ... class MyClass:
        ...     name: str
        ...
        >>> MyClassWithMeta = apply_metaclass(MyClass, RefMeta)
        >>> isinstance(MyClassWithMeta, RefMeta)
        True
    """
    # Get the class dict, excluding __dict__ and __weakref__
    class_dict: dict[str, Any] = {}
    for key, value in cls.__dict__.items():
        if key in ("__dict__", "__weakref__"):
            continue
        class_dict[key] = value

    # Create new class with the metaclass
    new_cls = metaclass(cls.__name__, cls.__bases__, class_dict)

    # Preserve module and qualname
    new_cls.__module__ = cls.__module__
    new_cls.__qualname__ = cls.__qualname__

    return new_cls  # type: ignore[no-any-return]
