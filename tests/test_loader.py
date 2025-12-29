"""Tests for the loader module."""

from dataclass_dsl._loader import (
    _ClassPlaceholder,
    _resolve_value,
    find_class_definitions,
    find_refs_in_source,
)


class TestFindRefsInSource:
    """Tests for find_refs_in_source function."""

    def test_ref_type_annotation(self):
        """Test matching Ref[ClassName] pattern."""
        source = """
class Object2:
    parent: Ref[Object1]
"""
        refs = find_refs_in_source(source)
        assert "Object1" in refs

    def test_attr_type_annotation(self):
        """Test matching Attr[ClassName, ...] pattern."""
        source = """
class Object2:
    parent_id: Attr[Object1, str]
"""
        refs = find_refs_in_source(source)
        assert "Object1" in refs

    def test_reflist_type_annotation(self):
        """Test matching RefList[ClassName] pattern."""
        source = """
class Object2:
    parents: RefList[Object1]
"""
        refs = find_refs_in_source(source)
        assert "Object1" in refs

    def test_refdict_type_annotation(self):
        """Test matching RefDict[..., ClassName] pattern."""
        source = """
class Object2:
    parents: RefDict[str, Object1]
"""
        refs = find_refs_in_source(source)
        assert "Object1" in refs

    def test_no_parens_attribute(self):
        """Test matching ClassName.Attribute pattern."""
        source = """
class Object2:
    parent_id = Object1.Id
"""
        refs = find_refs_in_source(source)
        assert "Object1" in refs

    def test_no_parens_class_reference(self):
        """Test matching = ClassName pattern."""
        source = """
class Object2:
    parent = Object1
"""
        refs = find_refs_in_source(source)
        assert "Object1" in refs

    def test_ref_function_call(self):
        """Test matching ref(ClassName) pattern."""
        source = """
class Object2:
    parent_id = ref(Object1)
"""
        refs = find_refs_in_source(source)
        assert "Object1" in refs

    def test_ref_function_does_not_match_strings(self):
        """Test that ref("string") is not matched."""
        source = """
class Object2:
    parent_id = ref("Object1")
"""
        refs = find_refs_in_source(source)
        assert "Object1" not in refs

    def test_get_att_function_call(self):
        """Test matching get_att(ClassName, ...) pattern."""
        source = """
class Object2:
    parent_arn = get_att(Object1, "Arn")
"""
        refs = find_refs_in_source(source)
        assert "Object1" in refs

    def test_get_att_function_does_not_match_strings(self):
        """Test that get_att("string", ...) is not matched."""
        source = """
class Object2:
    parent_arn = get_att("Object1", "Arn")
"""
        refs = find_refs_in_source(source)
        assert "Object1" not in refs

    def test_multiple_refs(self):
        """Test finding multiple references in one source."""
        source = """
class Object3:
    parent: Ref[Object1]
    other_id = ref(Object2)
    attr = get_att(Object4, "Arn")
"""
        refs = find_refs_in_source(source)
        assert refs == {"Object1", "Object2", "Object4"}


class TestFindClassDefinitions:
    """Tests for find_class_definitions function."""

    def test_single_class(self):
        """Test finding a single class definition."""
        source = """
class Object1:
    pass
"""
        classes = find_class_definitions(source)
        assert classes == ["Object1"]

    def test_multiple_classes(self):
        """Test finding multiple class definitions."""
        source = """
class Object1:
    pass

class Object2:
    pass
"""
        classes = find_class_definitions(source)
        assert classes == ["Object1", "Object2"]

    def test_class_with_base(self):
        """Test finding class with inheritance."""
        source = """
class Object1(Base):
    pass
"""
        classes = find_class_definitions(source)
        assert classes == ["Object1"]


class TestClassPlaceholder:
    """Tests for _ClassPlaceholder class."""

    def test_placeholder_repr(self):
        """Test placeholder repr."""
        placeholder = _ClassPlaceholder("MyClass", "mypackage.module")
        assert repr(placeholder) == "<Placeholder for mypackage.module.MyClass>"

    def test_placeholder_hash(self):
        """Test placeholder is hashable."""
        p1 = _ClassPlaceholder("MyClass", "mypackage.module")
        p2 = _ClassPlaceholder("MyClass", "mypackage.module")
        assert hash(p1) == hash(p2)

    def test_placeholder_equality(self):
        """Test placeholder equality."""
        p1 = _ClassPlaceholder("MyClass", "mypackage.module")
        p2 = _ClassPlaceholder("MyClass", "mypackage.module")
        p3 = _ClassPlaceholder("OtherClass", "mypackage.module")
        assert p1 == p2
        assert p1 != p3


class TestResolveValue:
    """Tests for _resolve_value function."""

    def test_resolve_placeholder(self):
        """Test resolving a placeholder to a real class."""

        class MyClass:
            pass

        placeholder = _ClassPlaceholder("MyClass", "test.module")
        class_map = {"MyClass": MyClass}
        result = _resolve_value(placeholder, class_map)
        assert result is MyClass

    def test_resolve_unresolved_placeholder(self):
        """Test placeholder without matching class returns itself."""
        placeholder = _ClassPlaceholder("Unknown", "test.module")
        class_map = {}
        result = _resolve_value(placeholder, class_map)
        assert result is placeholder

    def test_resolve_list_with_placeholders(self):
        """Test resolving placeholders in a list."""

        class A:
            pass

        class B:
            pass

        p_a = _ClassPlaceholder("A", "test")
        p_b = _ClassPlaceholder("B", "test")
        class_map = {"A": A, "B": B}
        result = _resolve_value([p_a, p_b], class_map)
        assert result == [A, B]

    def test_resolve_tuple_with_placeholders(self):
        """Test resolving placeholders in a tuple."""

        class A:
            pass

        p_a = _ClassPlaceholder("A", "test")
        class_map = {"A": A}
        result = _resolve_value((p_a, "literal"), class_map)
        assert result == (A, "literal")

    def test_resolve_dict_with_placeholders(self):
        """Test resolving placeholders in dict values."""

        class A:
            pass

        p_a = _ClassPlaceholder("A", "test")
        class_map = {"A": A}
        result = _resolve_value({"ref": p_a}, class_map)
        assert result == {"ref": A}

    def test_resolve_non_placeholder(self):
        """Test non-placeholder values pass through."""
        result = _resolve_value("literal", {})
        assert result == "literal"

        result = _resolve_value(42, {})
        assert result == 42

    def test_resolve_object_with_method(self):
        """Test object with _resolve_placeholders method is called."""

        class A:
            pass

        class MockIntrinsic:
            def __init__(self, placeholder):
                self.placeholder = placeholder

            def _resolve_placeholders(self, class_map):
                resolved = class_map.get(self.placeholder._name)
                return MockIntrinsic(resolved) if resolved else self

        p_a = _ClassPlaceholder("A", "test")
        intrinsic = MockIntrinsic(p_a)
        class_map = {"A": A}
        result = _resolve_value(intrinsic, class_map)
        assert result.placeholder is A
