"""
Runtime marker for attribute references in the no-parens pattern.

This module provides the AttrRef class, which is created when accessing
an attribute on a decorated class using the no-parens pattern:

    @refs
    class Object1:
        name: str = "object-1"

    Object1.Id  # Returns AttrRef(Object1, "Id")

AttrRef objects are detected by serializers and converted to the
appropriate format for the target domain.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

__all__ = ["AttrRef"]


class AttrRef:
    """
    Runtime marker for attribute references in the no-parens pattern.

    Created when accessing an undefined attribute on a decorated class:

        parent_id = Object1.Id  # Returns AttrRef(Object1, "Id")

    The serializer detects this and converts to the appropriate format.

    Attributes:
        target: The class being referenced (e.g., Object1)
        attr: The attribute name (e.g., "Id")

    Example:
        >>> @refs
        ... class Object1:
        ...     name: str = "object-1"
        ...
        >>> ref = Object1.Id
        >>> ref.target.__name__
        'Object1'
        >>> ref.attr
        'Id'
    """

    __slots__ = ("target", "attr")

    def __init__(self, target: type, attr: str) -> None:
        """
        Create an attribute reference marker.

        Args:
            target: The class being referenced (e.g., Object1)
            attr: The attribute name (e.g., "Id")
        """
        self.target = target
        self.attr = attr

    def __repr__(self) -> str:
        """Return a string representation of the AttrRef."""
        target_name = getattr(self.target, "__name__", str(self.target))
        return f"AttrRef({target_name}, {self.attr!r})"

    def __eq__(self, other: object) -> bool:
        """Check equality with another AttrRef."""
        if not isinstance(other, AttrRef):
            return NotImplemented
        return self.target is other.target and self.attr == other.attr

    def __hash__(self) -> int:
        """Return hash value for use in sets/dicts."""
        return hash((id(self.target), self.attr))

    def __getattr__(self, name: str) -> AttrRef:
        """Support chained attribute access like Object1.Endpoint.Address.

        When accessing a nested attribute on an AttrRef, this creates a new
        AttrRef with a dotted attribute path:

            Object1.Endpoint        # Returns AttrRef(Object1, "Endpoint")
            Object1.Endpoint.Address  # Returns AttrRef(Object1, "Endpoint.Address")

        This enables serializers to handle nested attribute references properly,
        for example generating {"Fn::GetAtt": ["Object1", "Endpoint.Address"]}
        in CloudFormation.

        Note: Dunder methods (e.g., __fspath__, __class__) are not intercepted
        to avoid breaking Python's internal protocols.
        """
        # Don't intercept dunder methods - they're Python internals
        if name.startswith("__") and name.endswith("__"):
            raise AttributeError(
                f"'{type(self).__name__}' object has no attribute '{name}'"
            )
        chained_attr = f"{self.attr}.{name}"
        return AttrRef(self.target, chained_attr)
