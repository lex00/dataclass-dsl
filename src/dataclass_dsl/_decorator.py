"""
Decorator factory for declarative dataclass resources.

This module provides create_decorator(), a factory that creates decorators
enabling the no-parens pattern for declarative DSLs.

The No-Parens Pattern:
    Instead of: parent = get_ref(Object1)
    Write:      parent = Object1

    Instead of: parent_id = get_attr(Object1, "Id")
    Write:      parent_id = Object1.Id

Example:
    # Domain package creates its own decorator
    from dataclass_dsl import create_decorator, ResourceRegistry

    registry = ResourceRegistry()

    refs = create_decorator(
        registry=registry,
        marker_attr="_my_marker",
        resource_field="resource",
    )

    # Users write declarative resources using no-parens pattern
    @refs
    class Object1:
        name: str = "object-1"

    @refs
    class Object2:
        parent = Object1        # No-parens class reference
        parent_id = Object1.Id  # No-parens attribute reference

    obj = Object2()  # No parameters needed!
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import MISSING
from dataclasses import dataclass as make_dataclass
from dataclasses import field as dc_field
from typing import Any, TypeVar, dataclass_transform

from dataclass_dsl._attr_ref import AttrRef
from dataclass_dsl._metaclass import RefMeta
from dataclass_dsl._registry import ResourceRegistry
from dataclass_dsl._utils import apply_metaclass

__all__ = ["create_decorator"]

T = TypeVar("T")

# Default marker attribute name
DEFAULT_MARKER = "_refs_marker"


@dataclass_transform()
def create_decorator(
    *,
    registry: ResourceRegistry | None = None,
    marker_attr: str = DEFAULT_MARKER,
    resource_field: str = "resource",
    pre_process: Callable[[type[T]], type[T]] | None = None,
    post_process: Callable[[type[T]], type[T]] | None = None,
    get_resource_type: Callable[[type[T]], type[Any] | str | None] | None = None,
) -> Callable[[type[T]], type[T]]:
    """
    Create a decorator for declarative dataclass resources.

    This factory creates decorators that:
    1. Apply @dataclass transformation
    2. Handle mutable defaults (lists, dicts)
    3. Apply RefMeta metaclass for no-parens attribute access
    4. Optionally register with a ResourceRegistry

    Args:
        registry: Optional registry for auto-registration.
        marker_attr: Attribute name to mark decorated classes.
            Defaults to "_refs_marker".
        resource_field: Name of the field to handle specially (e.g., "resource").
            If present without a value, gets None as default.
        pre_process: Optional hook called before dataclass transformation.
        post_process: Optional hook called after all transformations.
        get_resource_type: Optional function to extract the resource type
            from a decorated class. Used for registry type-based queries.

    Returns:
        A decorator function that can be applied to classes.

    Example:
        >>> registry = ResourceRegistry()
        >>> refs = create_decorator(registry=registry)
        >>>
        >>> @refs
        ... class MyResource:
        ...     name: str = "default"
        ...
        >>> "MyResource" in registry
        True
    """

    def decorator_factory(
        maybe_cls: type[T] | None = None,
        *,
        register: bool = True,
    ) -> type[T] | Callable[[type[T]], type[T]]:
        """
        The actual decorator (supports both @refs and @refs() syntax).

        Args:
            maybe_cls: The class to wrap (used when decorator called without parens).
            register: If True (default), auto-register with registry.

        Returns:
            The decorator function or the modified class.
        """

        def decorator(cls: type[T]) -> type[T]:
            """Apply transformations to the class."""
            # Run pre-process hook
            if pre_process is not None:
                cls = pre_process(cls)

            # Detect and handle all defaults (both mutable and immutable)
            # Mutable defaults (lists, dicts) -> field(default_factory=...)
            # Immutable defaults -> add annotation so they become dataclass fields
            for attr_name in list(vars(cls).keys()):
                if attr_name.startswith("_"):
                    continue

                attr_value = getattr(cls, attr_name, MISSING)
                if attr_value is MISSING:
                    continue

                # Skip class methods, staticmethods, properties, etc.
                if callable(attr_value) and not isinstance(attr_value, type):
                    continue
                if isinstance(attr_value, (classmethod, staticmethod, property)):
                    continue

                # Add type annotation if missing
                if not hasattr(cls, "__annotations__"):
                    cls.__annotations__ = {}
                if attr_name not in cls.__annotations__:
                    # Infer type from value
                    if isinstance(attr_value, list):
                        cls.__annotations__[attr_name] = list[Any]
                    elif isinstance(attr_value, dict):
                        cls.__annotations__[attr_name] = dict[str, Any]
                    elif isinstance(attr_value, type):
                        # This is a class reference (the no-parens pattern)
                        cls.__annotations__[attr_name] = type[Any]
                    elif isinstance(attr_value, AttrRef):
                        # This is an attribute reference (Object1.Id pattern)
                        cls.__annotations__[attr_name] = AttrRef
                    else:
                        cls.__annotations__[attr_name] = type(attr_value)

                # Check if this is a mutable default (list, dict, or class instance)
                if isinstance(attr_value, list):
                    # Convert to field(default_factory=...) with a copy
                    default_list = list(attr_value)
                    setattr(
                        cls,
                        attr_name,
                        dc_field(
                            default_factory=lambda v=default_list: list(v)  # type: ignore[misc]
                        ),
                    )
                elif isinstance(attr_value, dict):
                    # Convert to field(default_factory=...) with a copy
                    default_dict = dict(attr_value)
                    setattr(
                        cls,
                        attr_name,
                        dc_field(
                            default_factory=lambda v=default_dict: dict(v)  # type: ignore[misc]
                        ),
                    )
                elif isinstance(attr_value, AttrRef):
                    # AttrRef is immutable, use directly as default
                    pass
                elif hasattr(attr_value, "__class__") and not isinstance(
                    attr_value, (str, int, float, bool, type(None), type)
                ):
                    # Complex object - use copy if possible
                    import copy

                    try:
                        default_copy = copy.copy(attr_value)
                        setattr(
                            cls,
                            attr_name,
                            dc_field(
                                default_factory=lambda v=default_copy: copy.copy(v)  # type: ignore[misc]
                            ),
                        )
                    except Exception:
                        # If copy fails, fall back to returning the same instance
                        setattr(
                            cls,
                            attr_name,
                            dc_field(
                                default_factory=lambda v=attr_value: v  # type: ignore[misc]
                            ),
                        )

            # Add a default to the resource field if configured
            # Note: Use __dict__ directly to avoid triggering RefMeta.__getattr__
            # which would return an AttrRef instead of checking actual attribute
            if resource_field and hasattr(cls, "__annotations__"):
                if resource_field in cls.__annotations__:
                    if (
                        resource_field not in cls.__dict__
                        or cls.__dict__.get(resource_field) is MISSING
                    ):
                        setattr(cls, resource_field, None)

            # Store original __post_init__ if it exists
            original_post_init = getattr(cls, "__post_init__", None)

            def _refs_post_init(self: Any) -> None:
                """Post-init hook for decorated classes."""
                # Call original __post_init__ if it existed
                if original_post_init is not None:
                    original_post_init(self)

            # Add the __post_init__ method
            cls.__post_init__ = _refs_post_init  # type: ignore[attr-defined]

            # Apply @dataclass decorator
            cls = make_dataclass(cls)

            # Apply RefMeta metaclass to enable no-parens attribute access
            cls = apply_metaclass(cls, RefMeta)

            # Mark as a decorated class
            setattr(cls, marker_attr, True)

            # Run post-process hook
            if post_process is not None:
                cls = post_process(cls)

            # Auto-register if requested and registry is configured
            if register and registry is not None:
                resource_type: type[Any] | str | None = None
                if get_resource_type is not None:
                    resource_type = get_resource_type(cls)
                registry.register(cls, resource_type)

            return cls

        # Support both @refs and @refs() syntax
        if maybe_cls is None:
            return decorator
        return decorator(maybe_cls)

    return decorator_factory  # type: ignore[return-value]
