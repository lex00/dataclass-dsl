"""Integration tests for dataclass-dsl."""

import json
from typing import Annotated

from dataclass_dsl import (
    Provider,
    Ref,
    ResourceRegistry,
    Template,
    create_decorator,
    get_creation_order,
    get_deletion_order,
    is_attr_ref,
    is_class_ref,
)


class TestEndToEndWorkflow:
    """Test complete workflow from definition to serialization."""

    def test_full_workflow(self):
        """Test complete infrastructure definition workflow."""
        # Create registry and decorator
        registry = ResourceRegistry()
        refs = create_decorator(registry=registry)

        # Define resources (all with defaults for instantiation)
        @refs
        class Network:
            cidr: str = "10.0.0.0/16"
            name: str = "main-vpc"

        @refs
        class Subnet:
            network: Annotated[Network, Ref()] = None
            cidr: str = "10.0.1.0/24"
            az: str = "us-east-1a"

        @refs
        class SecurityGroup:
            network: Annotated[Network, Ref()] = None
            name: str = "web-sg"

        @refs
        class Instance:
            subnet: Annotated[Subnet, Ref()] = None
            security_group: Annotated[SecurityGroup, Ref()] = None
            instance_type: str = "t3.micro"

        # Verify registry
        assert len(registry) == 4
        assert Network in registry
        assert Subnet in registry
        assert SecurityGroup in registry
        assert Instance in registry

        # Build template
        template = Template.from_registry(
            registry=registry,
            description="Full workflow test",
        )

        assert len(template) == 4
        assert template.description == "Full workflow test"

        # Verify ordering
        ordered = template.get_dependency_order()
        names = [type(r).__name__ for r in ordered]

        # Network must come first
        assert names[0] == "Network"
        # Instance must come last
        assert names[-1] == "Instance"

    def test_no_parens_patterns(self):
        """Test all no-parens patterns work together."""
        refs = create_decorator()

        @refs
        class Role:
            name: str = "my-role"

        @refs
        class Network:
            cidr: str = "10.0.0.0/16"

        @refs
        class Function:
            # Class reference (no-parens)
            network = Network
            # Attribute reference (no-parens)
            role_arn = Role.Arn

        # Verify Function has correct defaults
        f = Function()

        # Class reference works
        assert f.network is Network
        assert is_class_ref(f.network)

        # Attribute reference works
        assert is_attr_ref(f.role_arn)
        assert f.role_arn.target is Role
        assert f.role_arn.attr == "Arn"

    def test_custom_provider(self):
        """Test custom provider serialization."""
        refs = create_decorator()

        @refs
        class Network:
            cidr: str = "10.0.0.0/16"

        @refs
        class Subnet:
            network: Annotated[Network, Ref()] = None
            cidr: str = "10.0.1.0/24"

        # Custom CloudFormation-like provider
        class CFProvider(Provider):
            name = "cloudformation"

            def serialize_ref(self, source, target):
                return {"Ref": target.__name__}

            def serialize_attr(self, source, target, attr_name):
                return {"Fn::GetAtt": [target.__name__, attr_name]}

            def serialize_resource(self, resource):
                props = {}
                for key, value in vars(resource).items():
                    if key.startswith("_"):
                        continue
                    if is_class_ref(value):
                        props[key] = {"Ref": value.__name__}
                    elif is_attr_ref(value):
                        props[key] = {"Fn::GetAtt": [value.target.__name__, value.attr]}
                    else:
                        props[key] = value
                return {
                    "Type": f"Custom::{type(resource).__name__}",
                    "Properties": props,
                }

        template = Template(description="CF-like output")
        template.add_resource(Network())
        template.add_resource(Subnet())

        provider = CFProvider()
        result = template.to_dict(provider=provider)

        # Verify structure
        assert result["Description"] == "CF-like output"
        assert "Network" in result["Resources"]
        assert "Subnet" in result["Resources"]

        # Verify resource format
        network = result["Resources"]["Network"]
        assert network["Type"] == "Custom::Network"
        assert network["Properties"]["cidr"] == "10.0.0.0/16"

    def test_creation_deletion_order(self):
        """Test resources are ordered correctly for creation/deletion."""
        refs = create_decorator()

        @refs
        class Database:
            name: str = "mydb"

        @refs
        class Cache:
            name: str = "mycache"

        @refs
        class App:
            database: Annotated[Database, Ref()] = None
            cache: Annotated[Cache, Ref()] = None

        @refs
        class LoadBalancer:
            app: Annotated[App, Ref()] = None

        classes = [LoadBalancer, App, Cache, Database]

        # Creation order: dependencies first
        creation = get_creation_order(classes)
        creation_names = [c.__name__ for c in creation]

        # Database and Cache have no deps, should come first
        assert creation_names.index("Database") < creation_names.index("App")
        assert creation_names.index("Cache") < creation_names.index("App")
        # App before LoadBalancer
        assert creation_names.index("App") < creation_names.index("LoadBalancer")

        # Deletion order: dependents first
        deletion = get_deletion_order(classes)
        deletion_names = [c.__name__ for c in deletion]

        # LoadBalancer should be deleted first
        assert deletion_names.index("LoadBalancer") < deletion_names.index("App")
        # App before Database/Cache
        assert deletion_names.index("App") < deletion_names.index("Database")
        assert deletion_names.index("App") < deletion_names.index("Cache")

    def test_instantiation_without_parameters(self):
        """Test decorated classes can be instantiated without parameters."""
        refs = create_decorator()

        @refs
        class ComplexResource:
            name: str = "default-name"
            tags: list = ["tag1", "tag2"]
            metadata: dict = {"key": "value"}
            count: int = 0
            enabled: bool = True

        # Should instantiate without any arguments
        r = ComplexResource()

        assert r.name == "default-name"
        assert r.tags == ["tag1", "tag2"]
        assert r.metadata == {"key": "value"}
        assert r.count == 0
        assert r.enabled is True

    def test_json_serialization(self):
        """Test complete JSON serialization."""
        refs = create_decorator()

        @refs
        class Resource:
            name: str = "test"
            count: int = 5

        template = Template(description="JSON test")
        template.add_resource(Resource())

        json_str = template.to_json(indent=2)

        # Should be valid JSON
        parsed = json.loads(json_str)

        assert parsed["description"] == "JSON test"
        assert "resources" in parsed

    def test_registry_scoping(self):
        """Test registry scoping by package."""
        registry = ResourceRegistry()
        refs = create_decorator(registry=registry)

        @refs
        class ProdNetwork:
            __module__ = "myapp.prod.network"

        @refs
        class DevNetwork:
            __module__ = "myapp.dev.network"

        @refs
        class SharedUtil:
            __module__ = "myapp.shared.utils"

        # All resources
        all_resources = registry.get_all()
        assert len(all_resources) == 3

        # Only prod
        prod = registry.get_all(scope_package="myapp.prod")
        assert len(prod) == 1
        assert ProdNetwork in prod

        # Only dev
        dev = registry.get_all(scope_package="myapp.dev")
        assert len(dev) == 1
        assert DevNetwork in dev

        # Shared
        shared = registry.get_all(scope_package="myapp.shared")
        assert len(shared) == 1
        assert SharedUtil in shared
