"""Tests for Provider abstract base class."""

import pytest

from dataclass_dsl import Provider, create_decorator


class TestProvider:
    """Tests for the Provider ABC."""

    def test_cannot_instantiate_abstract(self):
        """Test Provider cannot be instantiated directly."""
        with pytest.raises(TypeError):
            Provider()

    def test_concrete_provider(self):
        """Test creating a concrete provider."""

        class MyProvider(Provider):
            name = "test"

            def serialize_ref(self, source, target):
                return f"ref:{target.__name__}"

            def serialize_attr(self, source, target, attr_name):
                return f"attr:{target.__name__}.{attr_name}"

            def serialize_resource(self, resource):
                return {"name": type(resource).__name__}

        provider = MyProvider()
        assert provider.name == "test"

    def test_serialize_ref(self):
        """Test serialize_ref abstract method."""

        class RefProvider(Provider):
            name = "ref_test"

            def serialize_ref(self, source, target):
                return {"Ref": target.__name__}

            def serialize_attr(self, source, target, attr_name):
                return None

            def serialize_resource(self, resource):
                return {}

        provider = RefProvider()

        class SourceClass:
            pass

        class TargetClass:
            pass

        result = provider.serialize_ref(SourceClass, TargetClass)
        assert result == {"Ref": "TargetClass"}

    def test_serialize_attr(self):
        """Test serialize_attr abstract method."""

        class AttrProvider(Provider):
            name = "attr_test"

            def serialize_ref(self, source, target):
                return None

            def serialize_attr(self, source, target, attr_name):
                return {"GetAtt": [target.__name__, attr_name]}

            def serialize_resource(self, resource):
                return {}

        provider = AttrProvider()

        class SourceClass:
            pass

        class TargetClass:
            pass

        result = provider.serialize_attr(SourceClass, TargetClass, "Arn")
        assert result == {"GetAtt": ["TargetClass", "Arn"]}

    def test_serialize_resource(self):
        """Test serialize_resource abstract method."""
        refs = create_decorator()

        @refs
        class MyResource:
            name: str = "test-resource"

        class ResourceProvider(Provider):
            name = "resource_test"

            def serialize_ref(self, source, target):
                return None

            def serialize_attr(self, source, target, attr_name):
                return None

            def serialize_resource(self, resource):
                return {
                    "Type": type(resource).__name__,
                    "Properties": {"Name": resource.name},
                }

        provider = ResourceProvider()
        instance = MyResource()
        result = provider.serialize_resource(instance)

        assert result["Type"] == "MyResource"
        assert result["Properties"]["Name"] == "test-resource"

    def test_get_logical_id_default(self):
        """Test get_logical_id returns class name by default."""

        class SimpleProvider(Provider):
            name = "simple"

            def serialize_ref(self, source, target):
                return None

            def serialize_attr(self, source, target, attr_name):
                return None

            def serialize_resource(self, resource):
                return {}

        provider = SimpleProvider()

        class MyResource:
            pass

        assert provider.get_logical_id(MyResource) == "MyResource"

    def test_get_logical_id_custom(self):
        """Test get_logical_id respects _logical_id attribute."""

        class SimpleProvider(Provider):
            name = "simple"

            def serialize_ref(self, source, target):
                return None

            def serialize_attr(self, source, target, attr_name):
                return None

            def serialize_resource(self, resource):
                return {}

        provider = SimpleProvider()

        class MyResource:
            _logical_id = "CustomLogicalId"

        assert provider.get_logical_id(MyResource) == "CustomLogicalId"

    def test_repr(self):
        """Test provider string representation."""

        class SimpleProvider(Provider):
            name = "simple"

            def serialize_ref(self, source, target):
                return None

            def serialize_attr(self, source, target, attr_name):
                return None

            def serialize_resource(self, resource):
                return {}

        provider = SimpleProvider()
        assert "SimpleProvider" in repr(provider)
        assert "simple" in repr(provider)
