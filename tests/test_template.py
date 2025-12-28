"""Tests for Template base class."""

import json
from typing import Annotated

import pytest

from dataclass_dsl import (
    Provider,
    Ref,
    ResourceRegistry,
    Template,
    create_decorator,
)


@pytest.fixture
def registry():
    """Create a fresh registry."""
    return ResourceRegistry()


@pytest.fixture
def refs(registry):
    """Create a decorator with the registry."""
    return create_decorator(registry=registry)


class SimpleProvider(Provider):
    """Simple test provider."""

    name = "simple"

    def serialize_ref(self, source, target):
        return {"Ref": target.__name__}

    def serialize_attr(self, source, target, attr_name):
        return {"GetAtt": [target.__name__, attr_name]}

    def serialize_resource(self, resource):
        return {
            "Type": type(resource).__name__,
            "Properties": {
                k: v for k, v in vars(resource).items() if not k.startswith("_")
            },
        }


class TestTemplate:
    """Tests for Template class."""

    def test_create_empty_template(self):
        """Test creating empty template."""
        template = Template()
        assert template.description == ""
        assert template.resources == []
        assert len(template) == 0

    def test_create_with_description(self):
        """Test creating template with description."""
        template = Template(description="My infrastructure")
        assert template.description == "My infrastructure"

    def test_add_resource(self, refs):
        """Test adding resources to template."""

        @refs
        class MyResource:
            name: str = "test"

        template = Template()
        template.add_resource(MyResource())

        assert len(template) == 1

    def test_from_registry(self, registry, refs):
        """Test building template from registry."""

        @refs
        class Network:
            cidr: str = "10.0.0.0/16"

        @refs
        class Subnet:
            network: Annotated[Network, Ref()] = None

        template = Template.from_registry(
            registry=registry,
            description="Test stack",
        )

        assert template.description == "Test stack"
        assert len(template) == 2

    def test_from_registry_with_scope(self, registry, refs):
        """Test from_registry with scope filter."""

        @refs
        class ProdResource:
            __module__ = "myapp.prod.resources"
            name: str = "prod"

        @refs
        class DevResource:
            __module__ = "myapp.dev.resources"
            name: str = "dev"

        template = Template.from_registry(
            registry=registry,
            scope_package="myapp.prod",
        )

        # Only prod resources should be included
        resource_names = [type(r).__name__ for r in template.resources]
        assert "ProdResource" in resource_names
        assert "DevResource" not in resource_names

    def test_get_dependency_order(self, refs):
        """Test resources are ordered by dependencies."""

        @refs
        class Network:
            cidr: str = "10.0.0.0/16"

        @refs
        class Subnet:
            network: Annotated[Network, Ref()] = None

        @refs
        class Instance:
            subnet: Annotated[Subnet, Ref()] = None

        template = Template()
        # Add in wrong order
        template.add_resource(Instance())
        template.add_resource(Network())
        template.add_resource(Subnet())

        ordered = template.get_dependency_order()
        names = [type(r).__name__ for r in ordered]

        # Network should come first
        assert names.index("Network") < names.index("Subnet")
        assert names.index("Subnet") < names.index("Instance")

    def test_to_dict_generic(self, refs):
        """Test generic dict serialization."""

        @refs
        class MyResource:
            name: str = "test"

        template = Template(description="Test")
        template.add_resource(MyResource())

        result = template.to_dict()

        assert result["description"] == "Test"
        assert "resources" in result
        assert len(result["resources"]) == 1

    def test_to_dict_with_provider(self, refs):
        """Test dict serialization with provider."""

        @refs
        class MyResource:
            name: str = "test"

        template = Template(description="Test")
        template.add_resource(MyResource())

        provider = SimpleProvider()
        result = template.to_dict(provider=provider)

        assert result["Description"] == "Test"
        assert "Resources" in result
        assert "MyResource" in result["Resources"]

    def test_to_json(self, refs):
        """Test JSON serialization."""

        @refs
        class MyResource:
            name: str = "test"

        template = Template(description="Test")
        template.add_resource(MyResource())

        json_str = template.to_json()

        # Should be valid JSON
        parsed = json.loads(json_str)
        assert parsed["description"] == "Test"

    def test_to_json_with_provider(self, refs):
        """Test JSON serialization with provider."""

        @refs
        class MyResource:
            name: str = "test"

        template = Template(description="Test")
        template.add_resource(MyResource())

        provider = SimpleProvider()
        json_str = template.to_json(provider=provider)

        parsed = json.loads(json_str)
        assert parsed["Description"] == "Test"
        assert "MyResource" in parsed["Resources"]

    def test_validate_no_duplicates(self, refs):
        """Test validation passes with unique resources."""

        @refs
        class ResourceA:
            pass

        @refs
        class ResourceB:
            pass

        template = Template()
        template.add_resource(ResourceA())
        template.add_resource(ResourceB())

        errors = template.validate()
        assert errors == []

    def test_validate_duplicates(self, refs):
        """Test validation catches duplicate names."""

        @refs
        class MyResource:
            pass

        template = Template()
        template.add_resource(MyResource())
        template.add_resource(MyResource())  # Duplicate

        errors = template.validate()
        assert len(errors) > 0
        assert "Duplicate" in errors[0]

    def test_repr(self, refs):
        """Test template string representation."""

        @refs
        class MyResource:
            pass

        template = Template(description="Test stack")
        template.add_resource(MyResource())

        repr_str = repr(template)
        assert "Template" in repr_str
        assert "Test stack" in repr_str
        assert "1" in repr_str  # resource count

    def test_parameters(self):
        """Test template with parameters."""
        template = Template(
            parameters={"VpcCidr": {"Type": "String", "Default": "10.0.0.0/16"}}
        )
        assert "VpcCidr" in template.parameters

    def test_outputs(self):
        """Test template with outputs."""
        template = Template(outputs={"VpcId": {"Value": {"Ref": "MyVpc"}}})
        assert "VpcId" in template.outputs

    def test_conditions(self):
        """Test template with conditions."""
        template = Template(conditions={"IsProd": {"Equals": ["prod", "prod"]}})
        assert "IsProd" in template.conditions

    def test_mappings(self):
        """Test template with mappings."""
        template = Template(mappings={"RegionMap": {"us-east-1": {"AMI": "ami-123"}}})
        assert "RegionMap" in template.mappings

    def test_metadata(self):
        """Test template with metadata."""
        template = Template(metadata={"Version": "1.0"})
        assert template.metadata["Version"] == "1.0"
