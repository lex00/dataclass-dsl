"""Tests for AttrRef class."""

from dataclass_dsl import AttrRef


class TestAttrRef:
    """Tests for AttrRef runtime marker."""

    def test_create_attr_ref(self):
        """Test creating an AttrRef."""

        class MyClass:
            pass

        ref = AttrRef(MyClass, "Arn")
        assert ref.target is MyClass
        assert ref.attr == "Arn"

    def test_repr(self):
        """Test AttrRef string representation."""

        class MyRole:
            pass

        ref = AttrRef(MyRole, "Arn")
        assert repr(ref) == "AttrRef(MyRole, 'Arn')"

    def test_equality(self):
        """Test AttrRef equality comparison."""

        class MyClass:
            pass

        ref1 = AttrRef(MyClass, "Arn")
        ref2 = AttrRef(MyClass, "Arn")
        ref3 = AttrRef(MyClass, "Id")

        assert ref1 == ref2
        assert ref1 != ref3
        assert ref2 != ref3

    def test_equality_different_class(self):
        """Test AttrRef inequality with different classes."""

        class ClassA:
            pass

        class ClassB:
            pass

        ref1 = AttrRef(ClassA, "Arn")
        ref2 = AttrRef(ClassB, "Arn")

        assert ref1 != ref2

    def test_equality_non_attr_ref(self):
        """Test AttrRef equality with non-AttrRef objects."""

        class MyClass:
            pass

        ref = AttrRef(MyClass, "Arn")
        assert ref != "not an attr ref"
        assert ref != 42
        assert ref is not None

    def test_hashable(self):
        """Test AttrRef is hashable for use in sets/dicts."""

        class MyClass:
            pass

        ref1 = AttrRef(MyClass, "Arn")
        ref2 = AttrRef(MyClass, "Arn")
        ref3 = AttrRef(MyClass, "Id")

        # Can be used in sets
        ref_set = {ref1, ref2, ref3}
        assert len(ref_set) == 2  # ref1 and ref2 are equal

        # Can be used as dict keys
        ref_dict = {ref1: "value1", ref3: "value3"}
        assert ref_dict[ref2] == "value1"  # ref2 equals ref1

    def test_slots(self):
        """Test AttrRef uses __slots__ for memory efficiency."""
        assert hasattr(AttrRef, "__slots__")
        assert "target" in AttrRef.__slots__
        assert "attr" in AttrRef.__slots__

    def test_chained_attribute_access(self):
        """Test chained attribute access like Object.Endpoint.Address."""

        class Database:
            pass

        # First level creates AttrRef
        ref1 = AttrRef(Database, "Endpoint")
        assert ref1.target is Database
        assert ref1.attr == "Endpoint"

        # Chained access creates a new AttrRef with dotted path
        ref2 = ref1.Address
        assert ref2.target is Database
        assert ref2.attr == "Endpoint.Address"

    def test_multiple_chained_access(self):
        """Test multiple levels of chained attribute access."""

        class MyResource:
            pass

        ref1 = AttrRef(MyResource, "Level1")
        ref2 = ref1.Level2
        ref3 = ref2.Level3

        assert ref3.target is MyResource
        assert ref3.attr == "Level1.Level2.Level3"

    def test_chained_repr(self):
        """Test repr shows full dotted path for chained refs."""

        class MyDB:
            pass

        ref = AttrRef(MyDB, "Endpoint")
        chained = ref.Address
        assert repr(chained) == "AttrRef(MyDB, 'Endpoint.Address')"

    def test_chained_equality(self):
        """Test equality works correctly with chained refs."""

        class Resource:
            pass

        ref1 = AttrRef(Resource, "Endpoint").Address
        ref2 = AttrRef(Resource, "Endpoint.Address")

        # Both should be equal - same target and same attr path
        assert ref1 == ref2

    def test_chained_hashable(self):
        """Test chained AttrRefs are hashable."""

        class Resource:
            pass

        ref1 = AttrRef(Resource, "Endpoint").Address
        ref2 = AttrRef(Resource, "Endpoint.Address")
        ref3 = AttrRef(Resource, "Endpoint").Port

        # Can be used in sets
        ref_set = {ref1, ref2, ref3}
        assert len(ref_set) == 2  # ref1 and ref2 are equal

    def test_dunder_methods_raise_attribute_error(self):
        """Test that dunder methods are not intercepted by __getattr__."""
        import pytest

        class Resource:
            pass

        ref = AttrRef(Resource, "Endpoint")

        # Dunder methods should raise AttributeError, not create AttrRefs
        with pytest.raises(AttributeError):
            _ = ref.__fspath__

        with pytest.raises(AttributeError):
            _ = ref.__class_getitem__
