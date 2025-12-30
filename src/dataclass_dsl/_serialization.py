"""
Serialization framework for domain packages.

Provides base classes for field name mapping and value serialization
that domain packages can extend for their specific formats.

Example:
    >>> from dataclass_dsl._serialization import FieldMapper, ValueSerializer
    >>>
    >>> class PascalCaseMapper(FieldMapper):
    ...     def to_domain(self, name: str) -> str:
    ...         return ''.join(word.capitalize() for word in name.split('_'))
    ...
    ...     def from_domain(self, name: str) -> str:
    ...         import re
    ...         return re.sub(r'([A-Z])', r'_\\1', name).strip('_').lower()
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from dataclass_dsl._attr_ref import AttrRef

__all__ = [
    "FieldMapper",
    "PascalCaseMapper",
    "SnakeCaseMapper",
    "ValueSerializer",
]


class FieldMapper(ABC):
    """
    Abstract base class for field name mapping.

    Domain packages implement this to map between Python snake_case
    field names and their domain-specific format (e.g., PascalCase
    for CloudFormation, snake_case for Terraform).

    Example:
        >>> class MyMapper(FieldMapper):
        ...     def to_domain(self, name: str) -> str:
        ...         return name.upper()
        ...
        ...     def from_domain(self, name: str) -> str:
        ...         return name.lower()
    """

    @abstractmethod
    def to_domain(self, python_name: str) -> str:
        """
        Convert Python field name to domain format.

        Args:
            python_name: Python field name in snake_case.

        Returns:
            Domain-specific field name.

        Example:
            >>> mapper.to_domain("bucket_name")
            'BucketName'  # For CloudFormation
        """
        ...

    @abstractmethod
    def from_domain(self, domain_name: str) -> str:
        """
        Convert domain field name to Python format.

        Args:
            domain_name: Domain-specific field name.

        Returns:
            Python field name in snake_case.

        Example:
            >>> mapper.from_domain("BucketName")
            'bucket_name'
        """
        ...


class PascalCaseMapper(FieldMapper):
    """
    Maps Python snake_case to/from PascalCase.

    Used by CloudFormation and other PascalCase formats.

    Example:
        >>> mapper = PascalCaseMapper()
        >>> mapper.to_domain("bucket_name")
        'BucketName'
        >>> mapper.from_domain("BucketName")
        'bucket_name'
    """

    def to_domain(self, python_name: str) -> str:
        """Convert snake_case to PascalCase."""
        # Strip trailing underscore (used for Python keyword escape)
        if python_name.endswith("_") and not python_name.endswith("__"):
            python_name = python_name[:-1]
        return "".join(word.capitalize() for word in python_name.split("_"))

    def from_domain(self, domain_name: str) -> str:
        """Convert PascalCase to snake_case."""
        import re

        # Insert underscore before uppercase letters, then lowercase
        s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", domain_name)
        return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


class SnakeCaseMapper(FieldMapper):
    """
    Identity mapper for snake_case formats.

    Used by Terraform and other snake_case formats where
    Python and domain names are identical.

    Example:
        >>> mapper = SnakeCaseMapper()
        >>> mapper.to_domain("bucket_name")
        'bucket_name'
    """

    def to_domain(self, python_name: str) -> str:
        """Return name unchanged (already snake_case)."""
        return python_name

    def from_domain(self, domain_name: str) -> str:
        """Return name unchanged (already snake_case)."""
        return domain_name


class ValueSerializer(ABC):
    """
    Abstract base class for value serialization.

    Domain packages implement this to serialize Python values
    (including references and intrinsics) to their domain format.

    Example:
        >>> class CFSerializer(ValueSerializer):
        ...     def serialize_attr_ref(self, ref):
        ...         return {"Fn::GetAtt": [ref.target.__name__, ref.attr]}
        ...
        ...     def serialize_class_ref(self, cls):
        ...         return {"Ref": cls.__name__}
    """

    @abstractmethod
    def serialize_attr_ref(self, ref: AttrRef) -> Any:
        """
        Serialize an attribute reference (e.g., MyRole.Arn).

        Args:
            ref: The AttrRef instance to serialize.

        Returns:
            Domain-specific representation of the attribute reference.

        Example (CloudFormation):
            >>> serializer.serialize_attr_ref(AttrRef(MyRole, "Arn"))
            {'Fn::GetAtt': ['MyRole', 'Arn']}
        """
        ...

    @abstractmethod
    def serialize_class_ref(self, cls: type) -> Any:
        """
        Serialize a class reference (e.g., MyBucket).

        Args:
            cls: The class being referenced.

        Returns:
            Domain-specific representation of the class reference.

        Example (CloudFormation):
            >>> serializer.serialize_class_ref(MyBucket)
            {'Ref': 'MyBucket'}
        """
        ...

    def serialize(self, value: Any, field_name: str | None = None) -> Any:
        """
        Recursively serialize a value to domain format.

        Handles common types (lists, dicts, objects with to_dict),
        and delegates to abstract methods for references.

        Args:
            value: The value to serialize.
            field_name: Optional field name for context.

        Returns:
            Domain-specific serialized value.
        """
        from dataclass_dsl._attr_ref import AttrRef
        from dataclass_dsl._utils import is_class_ref

        # Handle AttrRef (e.g., MyRole.Arn)
        if isinstance(value, AttrRef):
            return self.serialize_attr_ref(value)

        # Handle class references (e.g., MyBucket)
        if is_class_ref(value):
            return self.serialize_class_ref(value)

        # Handle objects with to_dict() method
        if hasattr(value, "to_dict"):
            return value.to_dict()

        # Handle lists
        if isinstance(value, list):
            return [self.serialize(item, field_name) for item in value]

        # Handle dicts
        if isinstance(value, dict):
            return {k: self.serialize(v, field_name) for k, v in value.items()}

        # Return primitives as-is
        return value
