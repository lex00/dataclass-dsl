"""Tests for the loader module."""

import pytest

from dataclass_dsl._attr_ref import AttrRef
from dataclass_dsl._loader import (
    _auto_decorate_resources,
    _ClassPlaceholder,
    _resolve_value,
    _update_attr_refs,
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


class TestAutoDecorateResources:
    """Tests for _auto_decorate_resources function."""

    def test_decorates_class_with_resource_annotation(self):
        """Test that classes with resource annotation get decorated."""
        from dataclass_dsl import create_decorator

        class ResourceType:
            pass

        class MyResource:
            resource: ResourceType
            name = "test"

        decorator = create_decorator()
        package_globals = {"MyResource": MyResource}

        class_mapping = _auto_decorate_resources(package_globals, decorator)

        # Class should be decorated
        assert hasattr(package_globals["MyResource"], "_refs_marker")
        # Mapping should contain old -> new
        assert MyResource in class_mapping
        assert class_mapping[MyResource] is package_globals["MyResource"]

    def test_skips_class_without_resource_annotation(self):
        """Test that classes without resource annotation are not decorated."""
        from dataclass_dsl import create_decorator

        class NotAResource:
            name = "test"

        decorator = create_decorator()
        package_globals = {"NotAResource": NotAResource}

        class_mapping = _auto_decorate_resources(package_globals, decorator)

        # Class should not be decorated
        assert not hasattr(package_globals["NotAResource"], "_refs_marker")
        assert len(class_mapping) == 0

    def test_skips_already_decorated_class(self):
        """Test that already decorated classes are skipped."""
        from dataclass_dsl import create_decorator

        class ResourceType:
            pass

        decorator = create_decorator()

        @decorator
        class AlreadyDecorated:
            resource: ResourceType
            name = "test"

        original_class = AlreadyDecorated
        package_globals = {"AlreadyDecorated": AlreadyDecorated}

        class_mapping = _auto_decorate_resources(package_globals, decorator)

        # Class should not be re-decorated
        assert package_globals["AlreadyDecorated"] is original_class
        assert len(class_mapping) == 0

    def test_custom_resource_field(self):
        """Test using custom resource field name."""
        from dataclass_dsl import create_decorator

        class MyType:
            pass

        class MyResource:
            type_: MyType  # Using custom field name
            name = "test"

        decorator = create_decorator()
        package_globals = {"MyResource": MyResource}

        class_mapping = _auto_decorate_resources(
            package_globals, decorator, resource_field="type_"
        )

        # Class should be decorated
        assert hasattr(package_globals["MyResource"], "_refs_marker")
        assert MyResource in class_mapping

    def test_resource_predicate(self):
        """Test using resource_predicate for inheritance-based detection."""
        from dataclass_dsl import create_decorator

        class BaseResource:
            """Base class for resources."""

            pass

        class MyResource(BaseResource):
            name = "test"

        class NotAResource:
            name = "other"

        decorator = create_decorator()
        package_globals = {"MyResource": MyResource, "NotAResource": NotAResource}

        # Predicate detects subclasses of BaseResource
        def predicate(cls: type) -> bool:
            return (
                isinstance(cls, type)
                and issubclass(cls, BaseResource)
                and cls is not BaseResource
            )

        class_mapping = _auto_decorate_resources(
            package_globals, decorator, resource_predicate=predicate
        )

        # MyResource should be decorated (subclass of BaseResource)
        assert hasattr(package_globals["MyResource"], "_refs_marker")
        assert MyResource in class_mapping

        # NotAResource should NOT be decorated
        assert not hasattr(package_globals["NotAResource"], "_refs_marker")
        assert NotAResource not in class_mapping

    def test_resource_predicate_overrides_resource_field(self):
        """Test that resource_predicate takes precedence over resource_field."""
        from dataclass_dsl import create_decorator

        class BaseResource:
            pass

        class ResourceType:
            pass

        # This class has resource annotation but is NOT a BaseResource subclass
        class AnnotatedButNotSubclass:
            resource: ResourceType
            name = "test"

        # This class IS a BaseResource subclass but has no annotation
        class SubclassButNotAnnotated(BaseResource):
            name = "other"

        decorator = create_decorator()
        package_globals = {
            "AnnotatedButNotSubclass": AnnotatedButNotSubclass,
            "SubclassButNotAnnotated": SubclassButNotAnnotated,
        }

        # Predicate detects subclasses of BaseResource only
        def predicate(cls: type) -> bool:
            return (
                isinstance(cls, type)
                and issubclass(cls, BaseResource)
                and cls is not BaseResource
            )

        class_mapping = _auto_decorate_resources(
            package_globals, decorator, resource_predicate=predicate
        )

        # SubclassButNotAnnotated SHOULD be decorated (matches predicate)
        assert hasattr(package_globals["SubclassButNotAnnotated"], "_refs_marker")
        assert SubclassButNotAnnotated in class_mapping

        # AnnotatedButNotSubclass should NOT be decorated (doesn't match predicate)
        assert not hasattr(package_globals["AnnotatedButNotSubclass"], "_refs_marker")
        assert AnnotatedButNotSubclass not in class_mapping


class TestUpdateAttrRefs:
    """Tests for _update_attr_refs function."""

    def test_updates_attr_ref_targets(self):
        """Test that AttrRef targets are updated to decorated classes."""
        from dataclasses import dataclass, field

        class OldClass:
            pass

        class NewClass:
            pass

        # Create a dataclass with an AttrRef pointing to OldClass
        attr_ref = AttrRef(OldClass, "Arn")

        @dataclass
        class Consumer:
            ref: AttrRef = field(default=attr_ref)

        package_globals = {"Consumer": Consumer}
        class_mapping = {OldClass: NewClass}

        _update_attr_refs(package_globals, class_mapping)

        # AttrRef target should be updated
        assert attr_ref.target is NewClass

    def test_does_not_update_unmapped_refs(self):
        """Test that AttrRefs not in mapping are unchanged."""
        from dataclasses import dataclass, field

        class SomeClass:
            pass

        attr_ref = AttrRef(SomeClass, "Id")

        @dataclass
        class Consumer:
            ref: AttrRef = field(default=attr_ref)

        package_globals = {"Consumer": Consumer}
        class_mapping = {}  # Empty mapping

        _update_attr_refs(package_globals, class_mapping)

        # AttrRef target should be unchanged
        assert attr_ref.target is SomeClass

    def test_updates_class_reference_defaults(self):
        """Test that class reference defaults are updated to decorated classes."""
        from dataclasses import dataclass, fields

        class OldClass:
            pass

        class NewClass:
            pass

        @dataclass
        class Consumer:
            parent: type = OldClass

        package_globals = {"Consumer": Consumer}
        class_mapping = {OldClass: NewClass}

        _update_attr_refs(package_globals, class_mapping)

        # Field default should be updated
        consumer_fields = {f.name: f for f in fields(Consumer)}
        assert consumer_fields["parent"].default is NewClass


class TestSetupResourcesAutoDecorate:
    """Tests for setup_resources with auto_decorate option."""

    def test_auto_decorate_requires_decorator(self):
        """Test that auto_decorate=True requires decorator argument."""
        from dataclass_dsl import setup_resources

        with pytest.raises(ValueError, match="decorator is required"):
            setup_resources(
                __file__,
                "test.package",
                {},
                auto_decorate=True,
                decorator=None,
            )

    def test_auto_decorate_end_to_end(self, tmp_path):
        """Test auto-decoration with actual file loading."""
        from dataclass_dsl import create_decorator, setup_resources

        # Create a test package
        pkg_dir = tmp_path / "test_pkg"
        pkg_dir.mkdir()

        # Create __init__.py (will be populated by setup_resources)
        (pkg_dir / "__init__.py").write_text("")

        # Create a resource file with resource: annotation but no decorator
        (pkg_dir / "resources.py").write_text(
            """
from . import *

class ResourceType:
    pass

class MyResource:
    resource: ResourceType
    name = "test-resource"

class DependentResource:
    resource: ResourceType
    parent = MyResource
"""
        )

        # Run setup_resources with auto_decorate
        decorator = create_decorator()
        package_globals: dict = {}

        import sys

        # Add tmp_path to sys.path so imports work
        sys.path.insert(0, str(tmp_path))
        try:
            setup_resources(
                str(pkg_dir / "__init__.py"),
                "test_pkg",
                package_globals,
                auto_decorate=True,
                decorator=decorator,
                generate_stubs=False,
            )

            # Check that classes were loaded and decorated
            assert "MyResource" in package_globals
            assert "DependentResource" in package_globals

            # Check that they have the decorator marker
            assert hasattr(package_globals["MyResource"], "_refs_marker")
            assert hasattr(package_globals["DependentResource"], "_refs_marker")

            # Check that they're dataclasses
            import dataclasses

            assert dataclasses.is_dataclass(package_globals["MyResource"])
            assert dataclasses.is_dataclass(package_globals["DependentResource"])

            # Check that cross-references work
            dependent = package_globals["DependentResource"]
            fields = {f.name: f for f in dataclasses.fields(dependent)}
            assert fields["parent"].default is package_globals["MyResource"]

        finally:
            sys.path.remove(str(tmp_path))
            # Clean up sys.modules
            for mod_name in list(sys.modules.keys()):
                if mod_name.startswith("test_pkg"):
                    del sys.modules[mod_name]

    def test_resource_predicate_inheritance_pattern(self, tmp_path):
        """Test resource_predicate for inheritance-based resource detection."""
        from dataclass_dsl import create_decorator, setup_resources

        # Create a test package
        pkg_dir = tmp_path / "predicate_pkg"
        pkg_dir.mkdir()

        # Create __init__.py
        (pkg_dir / "__init__.py").write_text("")

        # Create base resource type and resources using inheritance
        (pkg_dir / "resources.py").write_text(
            """
class BaseResource:
    '''Base class for all resources.'''
    pass

class MyBucket(BaseResource):
    bucket_name = "my-data"

class NotAResource:
    '''Regular class, not a resource.'''
    name = "other"
"""
        )

        # Run setup_resources with resource_predicate
        decorator = create_decorator()
        package_globals: dict = {}

        import sys

        # Predicate for inheritance pattern
        def is_resource(cls: type) -> bool:
            # We need to check if it's a subclass of BaseResource
            # But BaseResource is defined in the module, so we check by name
            for base in cls.__mro__[1:]:  # Skip the class itself
                if base.__name__ == "BaseResource":
                    return True
            return False

        sys.path.insert(0, str(tmp_path))
        try:
            setup_resources(
                str(pkg_dir / "__init__.py"),
                "predicate_pkg",
                package_globals,
                auto_decorate=True,
                decorator=decorator,
                resource_predicate=is_resource,
                generate_stubs=False,
            )

            # Check that classes were loaded
            assert "BaseResource" in package_globals
            assert "MyBucket" in package_globals
            assert "NotAResource" in package_globals

            # MyBucket SHOULD be decorated (subclass of BaseResource)
            assert hasattr(package_globals["MyBucket"], "_refs_marker")

            # NotAResource should NOT be decorated
            assert not hasattr(package_globals["NotAResource"], "_refs_marker")

            # BaseResource itself should NOT be decorated (it's the base class)
            assert not hasattr(package_globals["BaseResource"], "_refs_marker")

        finally:
            sys.path.remove(str(tmp_path))
            # Clean up sys.modules
            for mod_name in list(sys.modules.keys()):
                if mod_name.startswith("predicate_pkg"):
                    del sys.modules[mod_name]
