"""
Intermediate Representation (IR) base classes for template parsing.

This module provides generic IR classes that domain packages can extend
or use directly for representing parsed templates.

The IR hierarchy:
    - IRTemplate: Top-level container for a template
    - IRResource: A resource with properties
    - IRParameter: A template parameter
    - IROutput: A template output
    - IRProperty: A property key-value pair

Example:
    >>> from dataclass_dsl._ir import IRTemplate, IRResource, IRProperty
    >>>
    >>> prop = IRProperty("BucketName", "bucket_name", "my-bucket")
    >>> resource = IRResource(
    ...     logical_id="MyBucket",
    ...     resource_type="AWS::S3::Bucket",
    ...     properties={"bucket_name": prop},
    ... )
    >>> template = IRTemplate(resources={"MyBucket": resource})
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

__all__ = [
    "IRProperty",
    "IRParameter",
    "IRResource",
    "IROutput",
    "IRTemplate",
]


@dataclass
class IRProperty:
    """A single property key-value pair within a resource.

    Properties can represent field name mappings between domain-specific
    naming conventions (e.g., PascalCase for CloudFormation) and Python's
    snake_case convention.

    Attributes:
        domain_name: Original property name in domain format (e.g., PascalCase).
        python_name: Converted property name in snake_case.
        value: Property value - may be a literal (str, int, bool), a
            domain-specific intrinsic, a list, a dict, or nested structures.

    Example:
        >>> prop = IRProperty("BucketName", "bucket_name", "my-bucket")
        >>> prop.python_name
        'bucket_name'
    """

    domain_name: str
    python_name: str
    value: Any


@dataclass
class IRParameter:
    """A parsed template parameter.

    Represents a parameter from a template's Parameters section,
    including common validation constraints.

    Attributes:
        logical_id: The parameter's logical name in the template.
        type: Parameter type (domain-specific, e.g., "String", "Number").
        description: Human-readable description of the parameter.
        default: Default value if none provided.
        allowed_values: List of permitted values.
        allowed_pattern: Regex pattern for validation.
        min_length: Minimum length for string parameters.
        max_length: Maximum length for string parameters.
        min_value: Minimum value for numeric parameters.
        max_value: Maximum value for numeric parameters.
        constraint_description: Message shown when validation fails.
        no_echo: If True, mask the parameter value.

    Example:
        >>> param = IRParameter("Environment", "String", default="dev")
        >>> param.default
        'dev'
    """

    logical_id: str
    type: str
    description: str | None = None
    default: Any | None = None
    allowed_values: list[Any] | None = None
    allowed_pattern: str | None = None
    min_length: int | None = None
    max_length: int | None = None
    min_value: int | None = None
    max_value: int | None = None
    constraint_description: str | None = None
    no_echo: bool = False


@dataclass
class IRResource:
    """A parsed resource.

    Represents a resource from a template's Resources section.
    Contains the resource type, all properties, and common resource-level
    attributes.

    Attributes:
        logical_id: The resource's logical name in the template.
        resource_type: Domain-specific resource type (e.g., "AWS::S3::Bucket",
            "google_storage_bucket", "aws_s3_bucket").
        properties: Dictionary of property python_name to IRProperty.
        depends_on: List of logical IDs this resource depends on.
        condition: Name of condition that controls resource creation.
        metadata: Domain-specific resource metadata.

    Example:
        >>> resource = IRResource(
        ...     logical_id="MyBucket",
        ...     resource_type="AWS::S3::Bucket",
        ... )
        >>> resource.logical_id
        'MyBucket'
    """

    logical_id: str
    resource_type: str
    properties: dict[str, IRProperty] = field(default_factory=dict)
    depends_on: list[str] = field(default_factory=list)
    condition: str | None = None
    metadata: dict[str, Any] | None = None


@dataclass
class IROutput:
    """A parsed template output.

    Represents an output from a template's Outputs section.
    Outputs expose values that can be referenced externally.

    Attributes:
        logical_id: The output's logical name in the template.
        value: The output value - may be a literal or domain-specific intrinsic.
        description: Human-readable description of the output.
        export_name: Name for cross-template/cross-stack exports.
        condition: Name of condition that controls whether output is created.

    Example:
        >>> output = IROutput("BucketArn", value={"Fn::GetAtt": ["MyBucket", "Arn"]})
        >>> output.logical_id
        'BucketArn'
    """

    logical_id: str
    value: Any
    description: str | None = None
    export_name: Any | None = None
    condition: str | None = None


@dataclass
class IRTemplate:
    """Complete parsed template.

    The top-level IR structure containing all parsed sections of a
    template. This is the main output of parsers and the primary
    input to code generators.

    Attributes:
        description: Template description.
        parameters: Dictionary of parameter name to IRParameter.
        resources: Dictionary of resource logical ID to IRResource.
        outputs: Dictionary of output name to IROutput.
        source_file: Path to the source template file (for error messages).
        reference_graph: Dependency graph of resource references. Maps logical
            ID to list of logical IDs it references.
        metadata: Domain-specific template metadata.

    Example:
        >>> template = IRTemplate(description="My stack")
        >>> template.resources["MyBucket"] = IRResource(
        ...     logical_id="MyBucket",
        ...     resource_type="AWS::S3::Bucket",
        ... )
        >>> len(template.resources)
        1
    """

    description: str | None = None
    parameters: dict[str, IRParameter] = field(default_factory=dict)
    resources: dict[str, IRResource] = field(default_factory=dict)
    outputs: dict[str, IROutput] = field(default_factory=dict)
    source_file: str | None = None
    reference_graph: dict[str, list[str]] = field(default_factory=dict)
    metadata: dict[str, Any] | None = None
