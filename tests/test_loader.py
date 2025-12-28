"""Tests for the loader module."""

from dataclass_dsl._loader import find_class_definitions, find_refs_in_source


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
