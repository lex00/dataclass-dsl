"""Tests for RefMeta metaclass."""

import pytest

from dataclass_dsl import AttrRef, RefMeta


class TestRefMeta:
    """Tests for RefMeta metaclass enabling no-parens pattern."""

    def test_undefined_attr_returns_attr_ref(self):
        """Test accessing undefined attribute returns AttrRef."""

        class MyResource(metaclass=RefMeta):
            defined_attr = "value"

        ref = MyResource.Arn
        assert isinstance(ref, AttrRef)
        assert ref.target is MyResource
        assert ref.attr == "Arn"

    def test_defined_attr_returns_value(self):
        """Test accessing defined attribute returns its value."""

        class MyResource(metaclass=RefMeta):
            defined_attr = "value"

        assert MyResource.defined_attr == "value"

    def test_dunder_attrs_not_intercepted(self):
        """Test dunder attributes are not intercepted."""

        class MyResource(metaclass=RefMeta):
            pass

        # Should raise AttributeError for missing dunder attrs
        with pytest.raises(AttributeError):
            _ = MyResource.__nonexistent__

    def test_reserved_attrs_not_intercepted(self):
        """Test reserved attributes are not intercepted."""

        class MyResource(metaclass=RefMeta):
            pass

        # These should raise AttributeError, not return AttrRef
        reserved = [
            "_refs_marker",
            "_wetwire_marker",
            "_abc_impl",
            "__dataclass_fields__",
        ]

        for attr in reserved:
            with pytest.raises(AttributeError):
                getattr(MyResource, attr)

    def test_methods_not_intercepted(self):
        """Test class methods work normally."""

        class MyResource(metaclass=RefMeta):
            @classmethod
            def my_method(cls):
                return "method result"

        assert MyResource.my_method() == "method result"

    def test_inheritance(self):
        """Test RefMeta works with inheritance."""

        class Parent(metaclass=RefMeta):
            parent_attr = "parent"

        class Child(Parent):
            child_attr = "child"

        # Both should return AttrRefs for undefined attrs
        assert isinstance(Parent.Arn, AttrRef)
        assert isinstance(Child.Arn, AttrRef)

        # Defined attrs work normally
        assert Parent.parent_attr == "parent"
        assert Child.parent_attr == "parent"
        assert Child.child_attr == "child"

    def test_multiple_attrs(self):
        """Test accessing multiple undefined attributes."""

        class MyRole(metaclass=RefMeta):
            pass

        arn_ref = MyRole.Arn
        id_ref = MyRole.Id
        name_ref = MyRole.Name

        assert arn_ref.attr == "Arn"
        assert id_ref.attr == "Id"
        assert name_ref.attr == "Name"
        assert arn_ref.target is MyRole
        assert id_ref.target is MyRole
        assert name_ref.target is MyRole
