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
