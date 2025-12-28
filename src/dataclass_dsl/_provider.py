"""
Abstract provider interface for format-specific serialization.

Domain packages implement this interface to provide format-specific
serialization logic for their target output format.

Example:
    >>> class MyProvider(Provider):
    ...     name = "myformat"
    ...
    ...     def serialize_ref(self, source, target):
    ...         return {"ref": target.__name__}
    ...
    ...     def serialize_attr(self, source, target, attr_name):
    ...         return {"attr": f"{target.__name__}.{attr_name}"}
    ...
    ...     def serialize_resource(self, resource):
    ...         return {"type": type(resource).__name__}
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from dataclass_dsl._template import Template

__all__ = ["Provider"]


class Provider(ABC):
    """
    Abstract provider for format-specific serialization.

    Subclasses implement domain-specific serialization logic for
    converting references and resources to target formats.

    Attributes:
        name: Provider identifier (e.g., "json", "yaml", "custom").

    Example:
        >>> class MyProvider(Provider):
        ...     name = "myformat"
        ...
        ...     def serialize_ref(self, source, target):
        ...         return f"ref:{target.__name__}"
        ...
        ...     def serialize_attr(self, source, target, attr_name):
        ...         return f"attr:{target.__name__}.{attr_name}"
        ...
        ...     def serialize_resource(self, resource):
        ...         return {"name": type(resource).__name__}
    """

    name: str  # Provider identifier

    @abstractmethod
    def serialize_ref(
        self,
        source: type[Any],
        target: type[Any],
    ) -> Any:
        """
        Serialize a reference from source to target.

        Args:
            source: The referencing class.
            target: The referenced class.

        Returns:
            Provider-specific reference representation.

        Example:
            {"ref": "Object1"}
        """
        ...

    @abstractmethod
    def serialize_attr(
        self,
        source: type[Any],
        target: type[Any],
        attr_name: str,
    ) -> Any:
        """
        Serialize an attribute reference (no-parens pattern).

        Args:
            source: The referencing class.
            target: The referenced class.
            attr_name: The attribute name.

        Returns:
            Provider-specific attribute reference representation.

        Example:
            {"attr": "Object1.Id"}
        """
        ...

    @abstractmethod
    def serialize_resource(
        self,
        resource: Any,
    ) -> dict[str, Any]:
        """
        Serialize a resource to provider format.

        Args:
            resource: The wrapper resource instance.

        Returns:
            Provider-specific resource representation.
        """
        ...

    def serialize_template(
        self,
        template: Template,
    ) -> dict[str, Any]:
        """
        Serialize a complete template.

        Default implementation builds a dict with serialized resources.
        Override for domain-specific template structure.

        Args:
            template: The Template to serialize.

        Returns:
            Provider-specific template representation.
        """
        resources: dict[str, Any] = {}
        for resource in template.get_dependency_order():
            logical_id = self.get_logical_id(type(resource))
            resources[logical_id] = self.serialize_resource(resource)

        result: dict[str, Any] = {}
        if template.description:
            result["Description"] = template.description
        if resources:
            result["Resources"] = resources
        if template.parameters:
            result["Parameters"] = template.parameters
        if template.outputs:
            result["Outputs"] = template.outputs
        if template.conditions:
            result["Conditions"] = template.conditions
        if template.mappings:
            result["Mappings"] = template.mappings
        if template.metadata:
            result["Metadata"] = template.metadata

        return result

    def get_logical_id(self, wrapper_cls: type[Any]) -> str:
        """
        Get the logical ID for a wrapper class.

        Args:
            wrapper_cls: The wrapper class.

        Returns:
            The logical ID string (default: class name).
        """
        return getattr(wrapper_cls, "_logical_id", wrapper_cls.__name__)

    def __repr__(self) -> str:
        """Return a string representation of the provider."""
        return f"{self.__class__.__name__}(name={self.name!r})"
