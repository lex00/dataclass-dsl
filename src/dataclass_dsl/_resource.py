"""
Base Resource class for infrastructure resources.

Domain packages extend this to provide domain-specific resource serialization.

Example:
    >>> class CloudFormationResource(Resource):
    ...     resource_type: ClassVar[str] = ""
    ...
    ...     def to_dict(self) -> dict:
    ...         return {"Type": self.resource_type, "Properties": ...}
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, ClassVar

__all__ = ["Resource"]


class Resource(ABC):
    """
    Abstract base class for infrastructure resources.

    Subclasses implement domain-specific serialization (CloudFormation,
    Terraform, GCP Deployment Manager, etc.).

    Attributes:
        resource_type: The domain-specific resource type identifier.
            For AWS: "AWS::S3::Bucket"
            For Terraform: "aws_s3_bucket"
            For GCP: "compute.v1.instance"

    Example:
        >>> from dataclass_dsl import Resource
        >>> from dataclasses import dataclass
        >>>
        >>> @dataclass
        ... class CloudFormationResource(Resource):
        ...     resource_type: ClassVar[str] = "AWS::Service::Resource"
        ...
        ...     def to_dict(self) -> dict:
        ...         return {"Type": self.resource_type, "Properties": {...}}
    """

    # Domain-specific resource type identifier
    resource_type: ClassVar[str] = ""

    @abstractmethod
    def to_dict(self) -> dict[str, Any]:
        """
        Serialize resource to dictionary format.

        Returns:
            Domain-specific dictionary representation.
        """
        ...

    @classmethod
    def get_resource_type(cls) -> str:
        """
        Return the resource type identifier.

        Returns:
            The domain-specific resource type string.
        """
        return cls.resource_type

    def __repr__(self) -> str:
        """Return a string representation of the resource."""
        return f"{self.__class__.__name__}()"
