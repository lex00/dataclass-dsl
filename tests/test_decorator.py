"""Tests for create_decorator factory."""

from dataclasses import fields
from typing import Any

from dataclass_dsl import (
    AttrRef,
    DecoratorType,
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

    def test_decorator_type_annotation(self):
        """Test decorator has proper type annotation using DecoratorType.

        Note: @dataclass_transform() makes type checkers interpret the return
        type specially. Use DecoratorType for explicit type annotations, but
        note that some type checkers may show warnings due to the interaction
        with @dataclass_transform().
        """
        refs = create_decorator()

        # The decorator should be usable with DecoratorType protocol
        # Note: @dataclass_transform() changes how type checkers see this,
        # so a type: ignore may be needed in practice
        def apply_decorator(
            decorator: DecoratorType,
            cls: type[Any],
        ) -> type[Any]:
            return decorator(cls)

        class TestClass:
            name: str = "test"

        # Should be able to use decorator in a typed function
        # Type checkers may complain due to @dataclass_transform() interaction
        result = apply_decorator(refs, TestClass)  # type: ignore[arg-type]
        assert hasattr(result, "__dataclass_fields__")

    def test_decorator_callable_signature(self):
        """Test decorator returned by create_decorator() is callable."""
        refs = create_decorator()

        # Test @refs syntax (direct call with class)
        class Class1:
            name: str = "one"

        result1 = refs(Class1)
        assert hasattr(result1, "__dataclass_fields__")

        # Test @refs() syntax (call without args returns decorator)
        decorator = refs()
        assert callable(decorator)

        class Class2:
            name: str = "two"

        result2 = decorator(Class2)
        assert hasattr(result2, "__dataclass_fields__")

    def test_attr_ref_target_identity(self):
        """Test that AttrRef targets have correct identity after decoration.

        When using the no-parens pattern (e.g., Role.Arn), the AttrRef.target
        should be the same object as the decorated class, not a different object.

        This is critical for identity comparison:
            role_ref = Function.role  # AttrRef
            role_ref.target is Role   # Should be True!

        Issue #10: Decorator was creating new class objects, breaking this.
        """
        refs = create_decorator()

        @refs
        class Role:
            name: str = "test-role"

        @refs
        class Function:
            role = Role.Arn  # AttrRef with target=Role

        # Get the AttrRef from the decorated class
        func = Function()
        role_ref = func.role

        # The AttrRef target MUST be the same object as the decorated Role
        assert isinstance(role_ref, AttrRef)
        assert role_ref.target is Role, (
            f"AttrRef.target should be identical to Role. "
            f"Got id(target)={id(role_ref.target)}, id(Role)={id(Role)}"
        )

    def test_class_ref_target_identity(self):
        """Test that class reference defaults have correct identity.

        When assigning a class directly (e.g., parent = Role), the default
        value should be the decorated class, not a pre-decoration version.
        """
        refs = create_decorator()

        @refs
        class Role:
            name: str = "test-role"

        @refs
        class Function:
            parent = Role  # Direct class reference

        # Get the class reference from the decorated class
        func = Function()

        # The default value MUST be the same object as the decorated Role
        assert func.parent is Role, (
            f"Class reference default should be identical to Role. "
            f"Got id(parent)={id(func.parent)}, id(Role)={id(Role)}"
        )

    def test_preserves_class_identity_when_metaclass_already_applied(self):
        """Test decorator preserves class identity when RefMeta already applied.

        When using setup_resources() with __build_class__ hook, RefMeta is
        applied during class definition for forward reference support.
        The decorator should NOT create a new class when RefMeta is already
        the metaclass, preserving class identity for AttrRef targets.

        Issue #10: Decorator was calling apply_metaclass() unconditionally,
        creating a new class even when RefMeta was already applied.
        """
        from dataclass_dsl._metaclass import RefMeta
        from dataclass_dsl._utils import apply_metaclass

        refs = create_decorator()

        # Simulate the loader's __build_class__ hook: apply RefMeta first
        class Role:
            name: str = "test-role"

        # Apply RefMeta (simulating what __build_class__ hook does)
        Role = apply_metaclass(Role, RefMeta)
        role_id_before = id(Role)

        # Now create Function that references Role.Arn
        class Function:
            role = Role.Arn  # AttrRef with target=Role (RefMeta-applied)

        Function = apply_metaclass(Function, RefMeta)

        # Apply the full decorator to both
        Role = refs(Role)
        Function = refs(Function)

        # After decoration, Role should be the SAME object (identity preserved)
        # because RefMeta was already applied
        assert id(Role) == role_id_before, (
            f"Decorator should NOT create new class when RefMeta already applied. "
            f"Expected id={role_id_before}, got id={id(Role)}"
        )

        # The AttrRef target should still point to the correct class
        func = Function()
        role_ref = func.role
        assert isinstance(role_ref, AttrRef)
        assert role_ref.target is Role, (
            f"AttrRef.target should be identical to decorated Role. "
            f"Got id(target)={id(role_ref.target)}, id(Role)={id(Role)}"
        )
