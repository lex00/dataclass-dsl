"""
PropertyType marker for nested property structures.

Domain packages extend this for nested structures within resources.

Example:
    >>> from dataclass_dsl import PropertyType
    >>> from dataclasses import dataclass
    >>>
    >>> @dataclass
    ... class VersioningConfiguration(PropertyType):
    ...     status: str = "Enabled"
    ...
    ...     def to_dict(self) -> dict:
    ...         return {"Status": self.status}
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

__all__ = ["PropertyType"]


class PropertyType(ABC):
    """
    Abstract base class for nested property types.

    Property types represent complex nested properties within resources,
    such as S3 Bucket's VersioningConfiguration or EC2 Instance's
    BlockDeviceMapping. They are not top-level resources.

    Domain packages extend this to provide field name mapping
    (e.g., snake_case to PascalCase for CloudFormation).

    Example:
        >>> @dataclass
        ... class Tag(PropertyType):
        ...     key: str = ""
        ...     value: str = ""
        ...
        ...     def to_dict(self) -> dict:
        ...         return {"Key": self.key, "Value": self.value}
    """

    @abstractmethod
    def to_dict(self) -> dict[str, Any]:
        """
        Serialize property type to dictionary format.

        Returns:
            Domain-specific dictionary representation with field name mapping.
        """
        ...

    def __repr__(self) -> str:
        """Return a string representation of the property type."""
        return f"{self.__class__.__name__}()"
