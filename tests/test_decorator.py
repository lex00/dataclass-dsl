"""Tests for create_decorator factory."""

from dataclasses import fields

from dataclass_dsl import (
    AttrRef,
    ResourceRegistry,
    create_decorator,
)


class TestCreateDecorator:
    """Tests for the decorator factory."""

    def test_basic_decorator(self):
        """Test basic decorator application."""
        refs = create_decorator()

        @refs
        class MyResource:
            name: str = "default"

        # Should be a dataclass
        assert hasattr(MyResource, "__dataclass_fields__")
        assert "name" in MyResource.__dataclass_fields__

        # Should be instantiable
        instance = MyResource()
        assert instance.name == "default"

    def test_decorator_with_registry(self):
        """Test decorator registers classes."""
        registry = ResourceRegistry()
        refs = create_decorator(registry=registry)

        @refs
        class MyResource:
            name: str = "test"

        assert MyResource in registry.get_all()

    def test_decorator_without_parens(self):
        """Test @refs syntax (without parens)."""
        refs = create_decorator()

        @refs
        class MyResource:
            name: str = "test"

        assert hasattr(MyResource, "__dataclass_fields__")

    def test_decorator_with_parens(self):
        """Test @refs() syntax (with parens)."""
        refs = create_decorator()

        @refs()
        class MyResource:
            name: str = "test"

        assert hasattr(MyResource, "__dataclass_fields__")

    def test_decorator_register_false(self):
        """Test @refs(register=False) skips registration."""
        registry = ResourceRegistry()
        refs = create_decorator(registry=registry)

        @refs(register=False)
        class MyResource:
            name: str = "test"

        assert MyResource not in registry.get_all()

    def test_mutable_defaults_list(self):
        """Test mutable list defaults are handled correctly."""
        refs = create_decorator()

        @refs
        class MyResource:
            tags: list = ["default"]

        # Each instance should get its own list
        r1 = MyResource()
        r2 = MyResource()
        r1.tags.append("new")

        assert "new" in r1.tags
        assert "new" not in r2.tags

    def test_mutable_defaults_dict(self):
        """Test mutable dict defaults are handled correctly."""
        refs = create_decorator()

        @refs
        class MyResource:
            metadata: dict = {"key": "value"}

        # Each instance should get its own dict
        r1 = MyResource()
        r2 = MyResource()
        r1.metadata["new"] = "data"

        assert "new" in r1.metadata
        assert "new" not in r2.metadata

    def test_no_parens_class_reference(self):
        """Test no-parens pattern with class reference."""
        registry = ResourceRegistry()
        refs = create_decorator(registry=registry)

        @refs
        class Network:
            cidr: str = "10.0.0.0/16"

        @refs
        class Subnet:
            vpc = Network  # No-parens class reference

        # Subnet should have Network as a default
        s = Subnet()
        assert s.vpc is Network

    def test_no_parens_attr_ref(self):
        """Test no-parens pattern with AttrRef."""
        refs = create_decorator()

        @refs
        class Role:
            name: str = "my-role"

        @refs
        class Function:
            role_arn = Role.Arn  # Returns AttrRef

        # Should have AttrRef as default
        f = Function()
        assert isinstance(f.role_arn, AttrRef)
        assert f.role_arn.target is Role
        assert f.role_arn.attr == "Arn"

    def test_marker_attr(self):
        """Test custom marker attribute."""
        refs = create_decorator(marker_attr="_custom_marker")

        @refs
        class MyResource:
            name: str = "test"

        assert hasattr(MyResource, "_custom_marker")
        assert MyResource._custom_marker is True

    def test_pre_process_hook(self):
        """Test pre_process hook is called."""
        processed = []

        def pre_hook(cls):
            processed.append(cls.__name__)
            return cls

        refs = create_decorator(pre_process=pre_hook)

        @refs
        class MyResource:
            name: str = "test"

        assert "MyResource" in processed

    def test_post_process_hook(self):
        """Test post_process hook is called."""
        processed = []

        def post_hook(cls):
            processed.append(cls.__name__)
            cls.extra_attr = "added"
            return cls

        refs = create_decorator(post_process=post_hook)

        @refs
        class MyResource:
            name: str = "test"

        assert "MyResource" in processed
        assert hasattr(MyResource, "extra_attr")
        assert MyResource.extra_attr == "added"

    def test_resource_field_default(self):
        """Test resource_field gets None as default."""
        refs = create_decorator(resource_field="resource")

        @refs
        class MyResource:
            resource: object  # Type annotation without value

        # Should be instantiable without providing resource
        r = MyResource()
        assert r.resource is None

    def test_ref_meta_applied(self):
        """Test RefMeta metaclass is applied."""
        refs = create_decorator()

        @refs
        class MyResource:
            name: str = "test"

        # Should return AttrRef for undefined attribute
        attr = MyResource.Arn
        assert isinstance(attr, AttrRef)

    def test_custom_post_init(self):
        """Test custom __post_init__ is preserved."""
        refs = create_decorator()

        class MyResource:
            name: str = "test"
            processed: bool = False

            def __post_init__(self):
                self.processed = True

        MyResource = refs(MyResource)

        r = MyResource()
        assert r.processed is True

    def test_dataclass_transform(self):
        """Test @dataclass_transform() for type checker support."""
        # This is mainly a compile-time check, but we can verify
        # the decorator creates proper dataclass behavior
        refs = create_decorator()

        @refs
        class MyResource:
            name: str
            count: int = 0

        # Should have all dataclass features
        assert hasattr(MyResource, "__dataclass_fields__")
        field_names = [f.name for f in fields(MyResource)]
        assert "name" in field_names
        assert "count" in field_names
