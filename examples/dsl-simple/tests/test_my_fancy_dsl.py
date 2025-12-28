"""Tests for MyFancyDSL example."""

import json

from my_fancy_dsl import (
    MyFancyDSLTemplate,
    get_all_dependencies,
    get_creation_order,
    get_deletion_order,
    registry,
)
from my_fancy_dsl.things import *  # noqa: F401, F403


class TestDecorator:
    """Test that @my_fancy_dsl decorator works correctly."""

    def test_classes_are_registered(self):
        """All decorated classes should be in the registry."""
        assert MyFancyThing1 in registry  # noqa: F405
        assert MyFancyThing2 in registry  # noqa: F405
        assert MyFancyThing3 in registry  # noqa: F405

    def test_classes_are_dataclasses(self):
        """Decorated classes should be dataclasses."""
        from dataclasses import fields

        assert len(fields(MyFancyThing1)) == 3  # noqa: F405
        assert len(fields(MyFancyThing2)) == 4  # noqa: F405
        assert len(fields(MyFancyThing3)) == 5  # noqa: F405

    def test_can_instantiate(self):
        """Can create instances with default values."""
        t1 = MyFancyThing1()  # noqa: F405
        assert t1.name == "thing1-default"
        assert t1.value == 100
        assert t1.tags == []

        t2 = MyFancyThing2()  # noqa: F405
        assert t2.name == "thing2-default"
        assert t2.enabled is True

        t3 = MyFancyThing3()  # noqa: F405
        assert t3.name == "thing3-default"
        assert t3.count == 0

    def test_can_instantiate_with_custom_values(self):
        """Can create instances with custom values."""
        t1 = MyFancyThing1(name="custom", value=42, tags=["a", "b"])  # noqa: F405
        assert t1.name == "custom"
        assert t1.value == 42
        assert t1.tags == ["a", "b"]


class TestDependencies:
    """Test dependency detection."""

    def test_thing1_has_no_dependencies(self):
        """MyFancyThing1 should have no dependencies."""
        deps = get_all_dependencies(MyFancyThing1)  # noqa: F405
        assert len(deps) == 0

    def test_thing2_depends_on_thing1(self):
        """MyFancyThing2 should depend on MyFancyThing1."""
        deps = get_all_dependencies(MyFancyThing2)  # noqa: F405
        assert MyFancyThing1 in deps  # noqa: F405

    def test_thing3_depends_on_thing2(self):
        """MyFancyThing3 should depend on MyFancyThing2."""
        deps = get_all_dependencies(MyFancyThing3)  # noqa: F405
        assert MyFancyThing2 in deps  # noqa: F405


class TestOrdering:
    """Test topological ordering."""

    def test_creation_order(self):
        """Things should be ordered with dependencies first."""
        things = [MyFancyThing3, MyFancyThing1, MyFancyThing2]  # noqa: F405
        order = get_creation_order(things)

        assert order.index(MyFancyThing1) < order.index(MyFancyThing2)  # noqa: F405
        assert order.index(MyFancyThing2) < order.index(MyFancyThing3)  # noqa: F405

    def test_deletion_order(self):
        """Deletion order should be reverse of creation order."""
        things = [MyFancyThing3, MyFancyThing1, MyFancyThing2]  # noqa: F405
        order = get_deletion_order(things)

        assert order.index(MyFancyThing3) < order.index(MyFancyThing2)  # noqa: F405
        assert order.index(MyFancyThing2) < order.index(MyFancyThing1)  # noqa: F405


class TestTemplate:
    """Test template aggregation and serialization."""

    def test_from_registry(self):
        """Template should collect all registered things."""
        template = MyFancyDSLTemplate.from_registry()
        assert len(template.resources) == 3

    def test_dependency_order(self):
        """Template should return things in dependency order."""
        template = MyFancyDSLTemplate.from_registry()
        order = template.get_dependency_order()
        names = [type(t).__name__ for t in order]

        assert names.index("MyFancyThing1") < names.index("MyFancyThing2")
        assert names.index("MyFancyThing2") < names.index("MyFancyThing3")

    def test_to_json(self):
        """Template should serialize to valid JSON."""
        template = MyFancyDSLTemplate.from_registry(
            description="Test template"
        )
        json_str = template.to_json()
        data = json.loads(json_str)

        assert data["Description"] == "Test template"
        assert "Resources" in data
        assert "MyFancyThing1" in data["Resources"]
        assert "MyFancyThing2" in data["Resources"]
        assert "MyFancyThing3" in data["Resources"]


class TestStarImport:
    """Test that the from . import * pattern works correctly."""

    def test_things_are_importable(self):
        """All things should be importable via star import."""
        # The star import at module level makes these available
        # We verify by checking they're callable classes
        assert callable(MyFancyThing1)  # noqa: F405
        assert callable(MyFancyThing2)  # noqa: F405
        assert callable(MyFancyThing3)  # noqa: F405

    def test_things_are_distinct_classes(self):
        """Each thing should be a distinct class."""
        assert MyFancyThing1 is not MyFancyThing2  # noqa: F405
        assert MyFancyThing2 is not MyFancyThing3  # noqa: F405
        assert MyFancyThing1 is not MyFancyThing3  # noqa: F405
