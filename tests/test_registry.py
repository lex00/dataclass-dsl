"""Tests for ResourceRegistry."""

import threading

from dataclass_dsl import ResourceRegistry, create_decorator


class TestResourceRegistry:
    """Tests for the ResourceRegistry class."""

    def test_register_class(self):
        """Test registering a class."""
        registry = ResourceRegistry()

        class MyResource:
            pass

        registry.register(MyResource)
        assert MyResource in registry.get_all()

    def test_register_with_resource_type(self):
        """Test registering with a resource type."""
        registry = ResourceRegistry()

        class NetworkType:
            pass

        class MyNetwork:
            pass

        registry.register(MyNetwork, resource_type=NetworkType)

        # Should be findable by type
        found = registry.get_by_type(NetworkType)
        assert MyNetwork in found

    def test_register_with_string_type(self):
        """Test registering with a string resource type."""
        registry = ResourceRegistry()

        class MyBucket:
            pass

        registry.register(MyBucket, resource_type="AWS::S3::Bucket")

        found = registry.get_by_type("AWS::S3::Bucket")
        assert MyBucket in found

    def test_get_all(self):
        """Test getting all registered classes."""
        registry = ResourceRegistry()

        class A:
            pass

        class B:
            pass

        class C:
            pass

        registry.register(A)
        registry.register(B)
        registry.register(C)

        all_classes = registry.get_all()
        assert A in all_classes
        assert B in all_classes
        assert C in all_classes
        assert len(all_classes) == 3

    def test_get_all_with_scope(self):
        """Test scoping by package prefix."""
        registry = ResourceRegistry()

        class ProdResource:
            __module__ = "myapp.prod.resources"

        class DevResource:
            __module__ = "myapp.dev.resources"

        registry.register(ProdResource)
        registry.register(DevResource)

        prod_only = registry.get_all(scope_package="myapp.prod")
        assert ProdResource in prod_only
        assert DevResource not in prod_only

    def test_contains(self):
        """Test 'in' operator."""
        registry = ResourceRegistry()

        class MyResource:
            pass

        class OtherResource:
            pass

        registry.register(MyResource)

        assert MyResource in registry
        assert OtherResource not in registry

    def test_len(self):
        """Test len() on registry."""
        registry = ResourceRegistry()

        class A:
            pass

        class B:
            pass

        assert len(registry) == 0
        registry.register(A)
        assert len(registry) == 1
        registry.register(B)
        assert len(registry) == 2

    def test_iter(self):
        """Test iterating over registry."""
        registry = ResourceRegistry()

        class A:
            pass

        class B:
            pass

        registry.register(A)
        registry.register(B)

        classes = list(registry)
        assert A in classes
        assert B in classes

    def test_clear(self):
        """Test clearing the registry."""
        registry = ResourceRegistry()

        class A:
            pass

        registry.register(A)
        assert len(registry) == 1

        registry.clear()
        assert len(registry) == 0
        assert A not in registry

    def test_get_by_name(self):
        """Test getting class by name."""
        registry = ResourceRegistry()

        class MyUniqueResource:
            pass

        registry.register(MyUniqueResource)

        found = registry.get_by_name("MyUniqueResource")
        assert found is MyUniqueResource

        not_found = registry.get_by_name("NonExistent")
        assert not_found is None

    def test_thread_safety(self):
        """Test registry is thread-safe."""
        registry = ResourceRegistry()
        errors = []

        def register_classes(prefix, count):
            try:
                for i in range(count):
                    cls = type(f"{prefix}Class{i}", (), {})
                    registry.register(cls)
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=register_classes, args=(f"Thread{t}_", 100))
            for t in range(10)
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(registry) == 1000

    def test_duplicate_registration(self):
        """Test registering same class twice is idempotent."""
        registry = ResourceRegistry()

        class MyResource:
            pass

        registry.register(MyResource)
        registry.register(MyResource)  # Should not raise or duplicate

        assert len(registry) == 1

    def test_repr(self):
        """Test registry string representation."""
        registry = ResourceRegistry()

        class A:
            pass

        class B:
            pass

        registry.register(A)
        registry.register(B)

        repr_str = repr(registry)
        assert "ResourceRegistry" in repr_str
        assert "2" in repr_str  # count


class TestRegistryWithDecorator:
    """Test registry integration with decorator."""

    def test_decorator_auto_registers(self):
        """Test decorator auto-registers classes."""
        registry = ResourceRegistry()
        refs = create_decorator(registry=registry)

        @refs
        class MyResource:
            name: str = "test"

        assert MyResource in registry

    def test_decorator_register_false(self):
        """Test decorator respects register=False."""
        registry = ResourceRegistry()
        refs = create_decorator(registry=registry)

        @refs(register=False)
        class MyResource:
            name: str = "test"

        assert MyResource not in registry
