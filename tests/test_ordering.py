"""Tests for dependency ordering utilities."""

from typing import Annotated

import pytest

from dataclass_dsl import (
    Ref,
    create_decorator,
    detect_cycles,
    get_all_dependencies,
    get_creation_order,
    get_deletion_order,
    get_dependency_graph,
    topological_sort,
)


@pytest.fixture
def refs():
    """Create a fresh decorator for tests."""
    return create_decorator()


class TestGetAllDependencies:
    """Tests for get_all_dependencies function."""

    def test_no_dependencies(self, refs):
        """Test class with no dependencies."""

        @refs
        class Network:
            cidr: str = "10.0.0.0/16"

        deps = get_all_dependencies(Network)
        assert len(deps) == 0

    def test_annotated_ref_dependency(self, refs):
        """Test Annotated[T, Ref()] creates dependency."""

        @refs
        class Network:
            cidr: str = "10.0.0.0/16"

        @refs
        class Subnet:
            network: Annotated[Network, Ref()] = None

        deps = get_all_dependencies(Subnet)
        assert Network in deps

    def test_no_parens_class_dependency(self, refs):
        """Test no-parens class reference creates dependency."""

        @refs
        class Network:
            cidr: str = "10.0.0.0/16"

        @refs
        class Subnet:
            vpc = Network

        deps = get_all_dependencies(Subnet)
        assert Network in deps

    def test_no_parens_attr_dependency(self, refs):
        """Test no-parens AttrRef creates dependency."""

        @refs
        class Role:
            name: str = "my-role"

        @refs
        class Function:
            role_arn = Role.Arn

        deps = get_all_dependencies(Function)
        assert Role in deps

    def test_multiple_dependencies(self, refs):
        """Test multiple dependencies."""

        @refs
        class Network:
            pass

        @refs
        class Role:
            pass

        @refs
        class SecurityGroup:
            pass

        @refs
        class Instance:
            network: Annotated[Network, Ref()] = None
            role = Role
            sg_id = SecurityGroup.GroupId

        deps = get_all_dependencies(Instance)
        assert Network in deps
        assert Role in deps
        assert SecurityGroup in deps


class TestTopologicalSort:
    """Tests for topological_sort function."""

    def test_empty_list(self):
        """Test sorting empty list."""
        result = topological_sort([])
        assert result == []

    def test_no_dependencies(self, refs):
        """Test sorting classes with no dependencies."""

        @refs
        class A:
            pass

        @refs
        class B:
            pass

        @refs
        class C:
            pass

        result = topological_sort([A, B, C])
        assert set(result) == {A, B, C}

    def test_linear_chain(self, refs):
        """Test sorting linear dependency chain."""

        @refs
        class Network:
            pass

        @refs
        class Subnet:
            network: Annotated[Network, Ref()] = None

        @refs
        class Instance:
            subnet: Annotated[Subnet, Ref()] = None

        result = topological_sort([Instance, Subnet, Network])

        # Network must come before Subnet
        assert result.index(Network) < result.index(Subnet)
        # Subnet must come before Instance
        assert result.index(Subnet) < result.index(Instance)

    def test_diamond_dependency(self, refs):
        """Test sorting diamond-shaped dependencies."""

        @refs
        class Network:
            pass

        @refs
        class SubnetA:
            network: Annotated[Network, Ref()] = None

        @refs
        class SubnetB:
            network: Annotated[Network, Ref()] = None

        @refs
        class Instance:
            subnet_a: Annotated[SubnetA, Ref()] = None
            subnet_b: Annotated[SubnetB, Ref()] = None

        result = topological_sort([Instance, SubnetA, SubnetB, Network])

        # Network must come before both subnets
        assert result.index(Network) < result.index(SubnetA)
        assert result.index(Network) < result.index(SubnetB)
        # Both subnets must come before Instance
        assert result.index(SubnetA) < result.index(Instance)
        assert result.index(SubnetB) < result.index(Instance)


class TestCreationDeletionOrder:
    """Tests for get_creation_order and get_deletion_order."""

    def test_creation_order(self, refs):
        """Test creation order puts dependencies first."""

        @refs
        class Network:
            pass

        @refs
        class Subnet:
            network: Annotated[Network, Ref()] = None

        @refs
        class Instance:
            subnet: Annotated[Subnet, Ref()] = None

        order = get_creation_order([Instance, Subnet, Network])

        assert order[0] is Network
        assert order[1] is Subnet
        assert order[2] is Instance

    def test_deletion_order(self, refs):
        """Test deletion order puts dependents first."""

        @refs
        class Network:
            pass

        @refs
        class Subnet:
            network: Annotated[Network, Ref()] = None

        @refs
        class Instance:
            subnet: Annotated[Subnet, Ref()] = None

        order = get_deletion_order([Instance, Subnet, Network])

        assert order[0] is Instance
        assert order[1] is Subnet
        assert order[2] is Network


class TestDetectCycles:
    """Tests for detect_cycles function."""

    def test_no_cycles(self, refs):
        """Test detection with no cycles."""

        @refs
        class A:
            pass

        @refs
        class B:
            a: Annotated[A, Ref()] = None

        @refs
        class C:
            b: Annotated[B, Ref()] = None

        cycles = detect_cycles([A, B, C])
        assert cycles == []

    def test_simple_cycle(self, refs):
        """Test detection of simple 2-node cycle."""
        # Create classes that reference each other
        # This requires forward reference pattern

        refs_decorator = refs

        @refs_decorator
        class A:
            pass

        @refs_decorator
        class B:
            a: Annotated[A, Ref()] = None

        # Manually add cycle for testing
        A.__annotations__["b"] = Annotated[B, Ref()]

        cycles = detect_cycles([A, B])
        assert len(cycles) >= 1


class TestDependencyGraph:
    """Tests for get_dependency_graph function."""

    def test_builds_graph(self, refs):
        """Test building dependency graph."""

        @refs
        class Network:
            pass

        @refs
        class Subnet:
            network: Annotated[Network, Ref()] = None

        @refs
        class Instance:
            subnet: Annotated[Subnet, Ref()] = None

        graph = get_dependency_graph([Network, Subnet, Instance])

        assert graph[Network] == set()
        assert graph[Subnet] == {Network}
        assert graph[Instance] == {Subnet}

    def test_graph_only_includes_listed_classes(self, refs):
        """Test graph only includes dependencies that are in the input list."""

        @refs
        class External:
            pass

        @refs
        class Internal:
            external: Annotated[External, Ref()] = None

        # External not in list
        graph = get_dependency_graph([Internal])

        # Should not include External since it's not in input
        assert graph[Internal] == set()
