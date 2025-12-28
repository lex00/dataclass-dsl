"""
Type markers for use with Annotated.

This module provides type markers that can be used with typing.Annotated
to indicate reference relationships between dataclasses. The type checker
sees the base type, while frameworks can detect the markers via introspection.

Usage:
    from typing import Annotated
    from dataclass_dsl import Ref, Attr, RefList, RefDict, ContextRef

    @dataclass
    class Subnet:
        network: Annotated[Network, Ref()]
        gateway_id: Annotated[str, Attr(Gateway, "Id")]
        security_groups: Annotated[list[SecurityGroup], RefList()]

The markers are:
- Ref: Indicates a reference to another class
- Attr: Indicates a reference to a specific attribute of another class
- RefList: Indicates a list of references
- RefDict: Indicates a dict with reference values
- ContextRef: Indicates a reference to a context value

Introspection functions:
- get_refs: Extract RefInfo from Annotated type hints
- get_dependencies: Get dependency classes from type hints
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import (
    Annotated,
    Any,
    Union,
    get_args,
    get_origin,
    get_type_hints,
)

__all__ = [
    "Ref",
    "Attr",
    "RefList",
    "RefDict",
    "ContextRef",
    "RefInfo",
    "get_refs",
    "get_dependencies",
]


class Ref:
    """
    Marker indicating a reference relationship.

    Use with Annotated to mark a field as referencing another class:

        network: Annotated[Network, Ref()]

    The type checker sees `Network`, frameworks see the `Ref()` marker.
    """

    def __repr__(self) -> str:
        return "Ref()"

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Ref)

    def __hash__(self) -> int:
        return hash(Ref)


class Attr:
    """
    Marker for attribute reference.

    Use with Annotated to mark a field as referencing an attribute of another class:

        gateway_id: Annotated[str, Attr(Gateway, "Id")]

    The type checker sees `str`, frameworks see the `Attr(Gateway, "Id")` marker.

    Attributes:
        target: The class being referenced.
        attr: The attribute name being referenced.
    """

    __slots__ = ("target", "attr")

    def __init__(self, target: type, attr: str) -> None:
        self.target = target
        self.attr = attr

    def __repr__(self) -> str:
        target_name = getattr(self.target, "__name__", str(self.target))
        return f"Attr({target_name}, {self.attr!r})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Attr):
            return NotImplemented
        return self.target is other.target and self.attr == other.attr

    def __hash__(self) -> int:
        return hash((Attr, id(self.target), self.attr))


class RefList:
    """
    Marker for list of references.

    Use with Annotated to mark a field as a list of references:

        security_groups: Annotated[list[SecurityGroup], RefList()]

    The type checker sees `list[SecurityGroup]`, frameworks see `RefList()`.
    """

    def __repr__(self) -> str:
        return "RefList()"

    def __eq__(self, other: object) -> bool:
        return isinstance(other, RefList)

    def __hash__(self) -> int:
        return hash(RefList)


class RefDict:
    """
    Marker for dict with reference values.

    Use with Annotated to mark a field as a dict with reference values:

        routes: Annotated[dict[str, Endpoint], RefDict()]

    The type checker sees `dict[str, Endpoint]`, frameworks see `RefDict()`.
    """

    def __repr__(self) -> str:
        return "RefDict()"

    def __eq__(self, other: object) -> bool:
        return isinstance(other, RefDict)

    def __hash__(self) -> int:
        return hash(RefDict)


class ContextRef:
    """
    Marker for context reference.

    Use with Annotated to mark a field as referencing a context value:

        region: Annotated[str, ContextRef("region")]

    The type checker sees `str`, frameworks see `ContextRef("region")`.

    Attributes:
        name: The context value name.
    """

    __slots__ = ("name",)

    def __init__(self, name: str) -> None:
        self.name = name

    def __repr__(self) -> str:
        return f"ContextRef({self.name!r})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ContextRef):
            return NotImplemented
        return self.name == other.name

    def __hash__(self) -> int:
        return hash((ContextRef, self.name))


@dataclass
class RefInfo:
    """
    Metadata about a reference field.

    Returned by get_refs() for each field that has a reference marker.

    Attributes:
        field: The field name.
        target: The referenced class (for Ref, Attr, RefList, RefDict).
        attr: The attribute name (for Attr markers).
        is_list: True if RefList marker.
        is_dict: True if RefDict marker.
        is_optional: True if the type is Optional (T | None).
        is_context: True if ContextRef marker.
    """

    field: str
    target: type | None
    attr: str | None = None
    is_list: bool = False
    is_dict: bool = False
    is_optional: bool = False
    is_context: bool = False


def _is_optional_type(tp: Any) -> bool:
    """Check if a type is Optional (Union with None)."""
    import types

    origin = get_origin(tp)
    # Handle typing.Union (e.g., Union[X, None] or Optional[X])
    if origin is Union:
        args = get_args(tp)
        return type(None) in args
    # Handle types.UnionType (e.g., X | None in Python 3.10+)
    if isinstance(tp, types.UnionType):
        args = get_args(tp)
        return type(None) in args
    return False


def _get_base_type_from_optional(tp: Any) -> Any:
    """Extract the non-None type from an Optional."""
    import types

    origin = get_origin(tp)
    # Handle typing.Union
    if origin is Union:
        args = get_args(tp)
        non_none = [a for a in args if a is not type(None)]
        if len(non_none) == 1:
            return non_none[0]
    # Handle types.UnionType (Python 3.10+)
    if isinstance(tp, types.UnionType):
        args = get_args(tp)
        non_none = [a for a in args if a is not type(None)]
        if len(non_none) == 1:
            return non_none[0]
    return tp


def _extract_target_from_type(tp: Any, is_list: bool, is_dict: bool) -> type | None:
    """Extract the target class from a type annotation."""
    # For list[T], get T
    if is_list:
        origin = get_origin(tp)
        if origin is list:
            args = get_args(tp)
            if args:
                return args[0] if isinstance(args[0], type) else None
        return None

    # For dict[K, V], get V
    if is_dict:
        origin = get_origin(tp)
        if origin is dict:
            args = get_args(tp)
            if len(args) >= 2:
                return args[1] if isinstance(args[1], type) else None
        return None

    # For plain type, return it
    if isinstance(tp, type):
        return tp

    return None


def get_refs(cls: type) -> dict[str, RefInfo]:
    """
    Extract reference information from Annotated type hints.

    Scans the class's type annotations for Annotated types with
    Ref, Attr, RefList, RefDict, or ContextRef markers.

    Args:
        cls: The class to analyze.

    Returns:
        Dict mapping field name to RefInfo.

    Example:
        >>> from typing import Annotated
        >>> from dataclasses import dataclass
        >>>
        >>> @dataclass
        ... class Subnet:
        ...     network: Annotated[Network, Ref()]
        ...     gateway_id: Annotated[str, Attr(Gateway, "Id")]
        ...
        >>> refs = get_refs(Subnet)
        >>> "network" in refs
        True
        >>> refs["network"].target
        <class 'Network'>
    """
    result: dict[str, RefInfo] = {}

    try:
        hints = get_type_hints(cls, include_extras=True)
    except Exception:
        return result

    for field_name, hint in hints.items():
        # Check if it's Annotated
        origin = get_origin(hint)
        if origin is not Annotated:
            continue

        args = get_args(hint)
        if not args:
            continue

        base_type = args[0]
        markers = args[1:]

        # Check for optional
        is_optional = _is_optional_type(base_type)
        if is_optional:
            base_type = _get_base_type_from_optional(base_type)

        # Look for our markers
        for marker in markers:
            if isinstance(marker, Ref):
                target = _extract_target_from_type(base_type, False, False)
                result[field_name] = RefInfo(
                    field=field_name,
                    target=target,
                    is_optional=is_optional,
                )
                break

            elif isinstance(marker, Attr):
                result[field_name] = RefInfo(
                    field=field_name,
                    target=marker.target,
                    attr=marker.attr,
                    is_optional=is_optional,
                )
                break

            elif isinstance(marker, RefList):
                target = _extract_target_from_type(base_type, True, False)
                result[field_name] = RefInfo(
                    field=field_name,
                    target=target,
                    is_list=True,
                    is_optional=is_optional,
                )
                break

            elif isinstance(marker, RefDict):
                target = _extract_target_from_type(base_type, False, True)
                result[field_name] = RefInfo(
                    field=field_name,
                    target=target,
                    is_dict=True,
                    is_optional=is_optional,
                )
                break

            elif isinstance(marker, ContextRef):
                result[field_name] = RefInfo(
                    field=field_name,
                    target=None,
                    attr=marker.name,
                    is_context=True,
                    is_optional=is_optional,
                )
                break

    return result


def get_dependencies(cls: type, transitive: bool = False) -> set[type]:
    """
    Get dependency classes from Annotated type hints.

    Extracts target classes from Ref, Attr, RefList, and RefDict markers.

    Args:
        cls: The class to analyze.
        transitive: If True, recursively get dependencies of dependencies.

    Returns:
        Set of classes this class depends on.

    Example:
        >>> from typing import Annotated
        >>> from dataclasses import dataclass
        >>>
        >>> @dataclass
        ... class Subnet:
        ...     network: Annotated[Network, Ref()]
        ...
        >>> deps = get_dependencies(Subnet)
        >>> Network in deps
        True
    """
    refs = get_refs(cls)
    deps: set[type] = set()

    for info in refs.values():
        if info.target is not None and not info.is_context:
            deps.add(info.target)

    if transitive and deps:
        visited: set[type] = {cls}
        to_process = list(deps)

        while to_process:
            current = to_process.pop()
            if current in visited:
                continue
            visited.add(current)

            sub_deps = get_dependencies(current, transitive=False)
            for sub_dep in sub_deps:
                if sub_dep not in visited:
                    deps.add(sub_dep)
                    to_process.append(sub_dep)

    return deps
