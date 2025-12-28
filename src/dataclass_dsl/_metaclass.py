"""
Metaclass enabling the no-parens attribute access pattern.

This module provides RefMeta, a metaclass that intercepts attribute access
on decorated classes to return AttrRef markers:

    @refs
    class Object1:
        name: str = "object-1"

    Object1.Id  # Returns AttrRef(Object1, "Id")

This enables the "no-parens" pattern where references are expressed as
simple class attribute access rather than function calls.
"""

from __future__ import annotations

from typing import Any

from dataclass_dsl._attr_ref import AttrRef

__all__ = ["RefMeta"]


class RefMeta(type):
    """
    Metaclass that enables the no-parens attribute access pattern.

    When a class uses this metaclass, accessing undefined class attributes
    returns an AttrRef marker:

        @refs
        class Object1:
            name: str = "object-1"

        Object1.Id  # Returns AttrRef(Object1, "Id")

    This allows clean, declarative syntax for expressing references between
    classes without function calls.

    Attributes:
        _RESERVED_ATTRS: Set of attribute names that should NOT return AttrRef.
            These include Python internals, dataclass internals, and common
            dunder methods.

    Example:
        >>> class MyMeta(RefMeta):
        ...     pass
        ...
        >>> class MyClass(metaclass=MyMeta):
        ...     pass
        ...
        >>> ref = MyClass.SomeAttr
        >>> isinstance(ref, AttrRef)
        True
        >>> ref.target is MyClass
        True
        >>> ref.attr
        'SomeAttr'
    """

    # Attributes that should NOT return AttrRef (Python internals, etc.)
    _RESERVED_ATTRS = frozenset(
        {
            # Python internals
            "__name__",
            "__qualname__",
            "__module__",
            "__dict__",
            "__doc__",
            "__annotations__",
            "__bases__",
            "__mro__",
            "__class__",
            "__weakref__",
            "__subclasshook__",
            "__init_subclass__",
            # Dataclass internals
            "__dataclass_fields__",
            "__dataclass_params__",
            "__post_init__",
            # Common dunder methods
            "__init__",
            "__new__",
            "__repr__",
            "__str__",
            "__eq__",
            "__hash__",
            "__reduce__",
            "__reduce_ex__",
            "__getstate__",
            "__setstate__",
            # Type checking
            "__origin__",
            "__args__",
            "__parameters__",
            # Marker attribute (configurable via decorator)
            "_refs_marker",
            "_resource_type",
        }
    )

    def __getattr__(cls, name: str) -> Any:
        """
        Return AttrRef for undefined attribute access (no-parens pattern).

        This enables patterns like:
            parent_id = Object1.Id  # AttrRef(Object1, "Id")

        Args:
            name: The attribute name being accessed.

        Returns:
            AttrRef marker for the attribute.

        Raises:
            AttributeError: If the attribute is reserved (starts with _ or
                is in _RESERVED_ATTRS).
        """
        # Don't intercept reserved attributes
        if name.startswith("_") or name in cls._RESERVED_ATTRS:
            raise AttributeError(
                f"type object {cls.__name__!r} has no attribute {name!r}"
            )

        # Return an AttrRef marker
        return AttrRef(cls, name)
