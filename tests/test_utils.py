"""Tests for helper utilities."""

from dataclasses import dataclass

from dataclass_dsl import (
    AttrRef,
    RefMeta,
    apply_metaclass,
    create_decorator,
    get_ref_target,
    is_attr_ref,
    is_class_ref,
)


class TestIsAttrRef:
    """Tests for is_attr_ref function."""

    def test_attr_ref_returns_true(self):
        """Test AttrRef returns True."""

        class MyClass:
            pass

        ref = AttrRef(MyClass, "Arn")
        assert is_attr_ref(ref) is True

    def test_non_attr_ref_returns_false(self):
        """Test non-AttrRef returns False."""
        assert is_attr_ref("string") is False
        assert is_attr_ref(42) is False
        assert is_attr_ref(None) is False
        assert is_attr_ref([]) is False
        assert is_attr_ref({}) is False

    def test_class_returns_false(self):
        """Test class itself returns False."""

        class MyClass:
            pass

        assert is_attr_ref(MyClass) is False


class TestIsClassRef:
    """Tests for is_class_ref function."""

    def test_decorated_class_returns_true(self):
        """Test decorated class returns True."""
        refs = create_decorator()

        @refs
        class MyResource:
            pass

        assert is_class_ref(MyResource) is True

    def test_undecorated_class_returns_false(self):
        """Test undecorated class returns False."""

        class PlainClass:
            pass

        assert is_class_ref(PlainClass) is False

    def test_custom_marker(self):
        """Test custom marker attribute."""
        refs = create_decorator(marker_attr="_custom_marker")

        @refs
        class MyResource:
            pass

        # Default marker should not find it
        assert is_class_ref(MyResource) is False

        # Custom marker should find it
        assert is_class_ref(MyResource, marker="_custom_marker") is True

    def test_non_class_returns_false(self):
        """Test non-class objects return False."""
        assert is_class_ref("string") is False
        assert is_class_ref(42) is False
        assert is_class_ref(None) is False


class TestGetRefTarget:
    """Tests for get_ref_target function."""

    def test_attr_ref_returns_target(self):
        """Test AttrRef returns its target."""

        class MyClass:
            pass

        ref = AttrRef(MyClass, "Arn")
        assert get_ref_target(ref) is MyClass

    def test_class_returns_itself(self):
        """Test class returns itself."""

        class MyClass:
            pass

        assert get_ref_target(MyClass) is MyClass

    def test_non_ref_returns_none(self):
        """Test non-ref returns None."""
        assert get_ref_target("string") is None
        assert get_ref_target(42) is None
        assert get_ref_target(None) is None


class TestApplyMetaclass:
    """Tests for apply_metaclass function."""

    def test_applies_metaclass(self):
        """Test metaclass is applied."""

        @dataclass
        class MyClass:
            name: str = "test"

        NewClass = apply_metaclass(MyClass, RefMeta)

        # Should have RefMeta behavior
        ref = NewClass.UndefinedAttr
        assert isinstance(ref, AttrRef)

    def test_preserves_attributes(self):
        """Test class attributes are preserved."""

        @dataclass
        class MyClass:
            name: str = "test"
            count: int = 0

        NewClass = apply_metaclass(MyClass, RefMeta)

        # Should still be a dataclass
        assert hasattr(NewClass, "__dataclass_fields__")

        # Should be instantiable
        instance = NewClass()
        assert instance.name == "test"
        assert instance.count == 0

    def test_preserves_module(self):
        """Test __module__ is preserved."""

        @dataclass
        class MyClass:
            name: str = "test"

        original_module = MyClass.__module__
        NewClass = apply_metaclass(MyClass, RefMeta)

        assert NewClass.__module__ == original_module

    def test_preserves_qualname(self):
        """Test __qualname__ is preserved."""

        @dataclass
        class MyClass:
            name: str = "test"

        original_qualname = MyClass.__qualname__
        NewClass = apply_metaclass(MyClass, RefMeta)

        assert NewClass.__qualname__ == original_qualname
