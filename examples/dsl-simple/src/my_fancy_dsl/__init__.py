"""
MyFancyDSL - Example DSL using dataclass-dsl.

This package demonstrates how to build a declarative DSL with:
- Custom decorator (@my_fancy_dsl)
- Multi-file organization with `from . import *`
- Automatic dependency detection and ordering
- Template aggregation and JSON serialization
"""

from typing import Any

from dataclass_dsl import (
    Provider,
    ResourceRegistry,
    Template,
    create_decorator,
    get_all_dependencies,
    get_creation_order,
    get_deletion_order,
)

# Registry for all decorated things
registry = ResourceRegistry()

# Create the @my_fancy_dsl decorator
my_fancy_dsl = create_decorator(registry=registry)


class MyFancyDSLProvider(Provider):
    """Provider for serializing MyFancyDSL things to JSON-friendly format."""

    name = "my_fancy_dsl"

    def serialize_ref(self, source: type[Any], target: type[Any]) -> dict[str, Any]:
        """Serialize a class reference."""
        return {"$ref": target.__name__}

    def serialize_attr(
        self, source: type[Any], target: type[Any], attr_name: str
    ) -> dict[str, Any]:
        """Serialize an attribute reference."""
        return {"$attr": f"{target.__name__}.{attr_name}"}

    def serialize_resource(self, resource: Any) -> dict[str, Any]:
        """Serialize a thing instance."""
        properties = {}
        for k, v in vars(resource).items():
            if k.startswith("_"):
                continue
            # Skip reference fields (class refs and AttrRef objects)
            if isinstance(v, type) or hasattr(v, "_target_class"):
                continue
            properties[k] = v
        return {
            "type": type(resource).__name__,
            "properties": properties,
        }


class MyFancyDSLTemplate(Template):
    """Template for collecting and serializing MyFancyDSL things."""

    @classmethod
    def from_registry(
        cls,
        description: str = "",
        scope_package: str | None = None,
    ) -> "MyFancyDSLTemplate":
        """Create a template from all registered things."""
        return super().from_registry(
            registry=registry,
            description=description,
            scope_package=scope_package,
        )

    def to_json(self, indent: int = 2) -> str:
        """Serialize to JSON using MyFancyDSLProvider."""
        return super().to_json(provider=MyFancyDSLProvider(), indent=indent)


__all__ = [
    # Decorator
    "my_fancy_dsl",
    # Registry
    "registry",
    # Provider and Template
    "MyFancyDSLProvider",
    "MyFancyDSLTemplate",
    # Re-exported utilities
    "get_all_dependencies",
    "get_creation_order",
    "get_deletion_order",
]
