"""Tests for Annotated-based type markers."""

from dataclasses import dataclass
from typing import Annotated

from dataclass_dsl import (
    Attr,
    ContextRef,
    Ref,
    RefDict,
    RefInfo,
    RefList,
    get_dependencies,
    get_refs,
)


class TestRef:
    """Tests for Ref marker class."""

    def test_create_ref(self):
        """Test creating a Ref marker."""
        ref = Ref()
        assert isinstance(ref, Ref)

    def test_repr(self):
        """Test Ref string representation."""
        ref = Ref()
        assert repr(ref) == "Ref()"

    def test_equality(self):
        """Test Ref equality - all Refs are equal."""
        ref1 = Ref()
        ref2 = Ref()
        assert ref1 == ref2

    def test_hashable(self):
        """Test Ref is hashable."""
        ref1 = Ref()
        ref2 = Ref()
        ref_set = {ref1, ref2}
        assert len(ref_set) == 1


class TestAttr:
    """Tests for Attr marker class."""

    def test_create_attr(self):
        """Test creating an Attr marker."""

        class Target:
            pass

        attr = Attr(Target, "Arn")
        assert attr.target is Target
        assert attr.attr == "Arn"

    def test_repr(self):
        """Test Attr string representation."""

        class MyRole:
            pass

        attr = Attr(MyRole, "Arn")
        assert repr(attr) == "Attr(MyRole, 'Arn')"

    def test_equality(self):
        """Test Attr equality comparison."""

        class Target:
            pass

        attr1 = Attr(Target, "Arn")
        attr2 = Attr(Target, "Arn")
        attr3 = Attr(Target, "Id")

        assert attr1 == attr2
        assert attr1 != attr3

    def test_equality_different_target(self):
        """Test Attr inequality with different targets."""

        class TargetA:
            pass

        class TargetB:
            pass

        attr1 = Attr(TargetA, "Arn")
        attr2 = Attr(TargetB, "Arn")

        assert attr1 != attr2

    def test_hashable(self):
        """Test Attr is hashable."""

        class Target:
            pass

        attr1 = Attr(Target, "Arn")
        attr2 = Attr(Target, "Arn")
        attr_set = {attr1, attr2}
        assert len(attr_set) == 1


class TestRefList:
    """Tests for RefList marker class."""

    def test_create_reflist(self):
        """Test creating a RefList marker."""
        ref_list = RefList()
        assert isinstance(ref_list, RefList)

    def test_repr(self):
        """Test RefList string representation."""
        ref_list = RefList()
        assert repr(ref_list) == "RefList()"

    def test_equality(self):
        """Test RefList equality - all RefLists are equal."""
        ref1 = RefList()
        ref2 = RefList()
        assert ref1 == ref2


class TestRefDict:
    """Tests for RefDict marker class."""

    def test_create_refdict(self):
        """Test creating a RefDict marker."""
        ref_dict = RefDict()
        assert isinstance(ref_dict, RefDict)

    def test_repr(self):
        """Test RefDict string representation."""
        ref_dict = RefDict()
        assert repr(ref_dict) == "RefDict()"


class TestContextRef:
    """Tests for ContextRef marker class."""

    def test_create_context_ref(self):
        """Test creating a ContextRef marker."""
        ctx = ContextRef("region")
        assert ctx.name == "region"

    def test_repr(self):
        """Test ContextRef string representation."""
        ctx = ContextRef("region")
        assert repr(ctx) == "ContextRef('region')"

    def test_equality(self):
        """Test ContextRef equality comparison."""
        ctx1 = ContextRef("region")
        ctx2 = ContextRef("region")
        ctx3 = ContextRef("account")

        assert ctx1 == ctx2
        assert ctx1 != ctx3


class TestGetRefs:
    """Tests for get_refs function."""

    def test_ref_marker(self):
        """Test detecting Ref marker."""

        class Network:
            pass

        @dataclass
        class Subnet:
            network: Annotated[Network, Ref()]

        refs = get_refs(Subnet)
        assert "network" in refs
        assert refs["network"].target is Network
        assert refs["network"].is_list is False
        assert refs["network"].is_dict is False

    def test_attr_marker(self):
        """Test detecting Attr marker."""

        class Role:
            pass

        @dataclass
        class Function:
            role_arn: Annotated[str, Attr(Role, "Arn")]

        refs = get_refs(Function)
        assert "role_arn" in refs
        assert refs["role_arn"].target is Role
        assert refs["role_arn"].attr == "Arn"

    def test_reflist_marker(self):
        """Test detecting RefList marker."""

        class SecurityGroup:
            pass

        @dataclass
        class Instance:
            security_groups: Annotated[list[SecurityGroup], RefList()]

        refs = get_refs(Instance)
        assert "security_groups" in refs
        assert refs["security_groups"].target is SecurityGroup
        assert refs["security_groups"].is_list is True

    def test_refdict_marker(self):
        """Test detecting RefDict marker."""

        class Endpoint:
            pass

        @dataclass
        class Service:
            routes: Annotated[dict[str, Endpoint], RefDict()]

        refs = get_refs(Service)
        assert "routes" in refs
        assert refs["routes"].target is Endpoint
        assert refs["routes"].is_dict is True

    def test_context_ref_marker(self):
        """Test detecting ContextRef marker."""

        @dataclass
        class Resource:
            region: Annotated[str, ContextRef("region")]

        refs = get_refs(Resource)
        assert "region" in refs
        assert refs["region"].is_context is True
        assert refs["region"].attr == "region"
        assert refs["region"].target is None

    def test_optional_ref(self):
        """Test detecting optional Ref."""

        class Network:
            pass

        @dataclass
        class Subnet:
            network: Annotated[Network | None, Ref()] = None

        refs = get_refs(Subnet)
        assert "network" in refs
        assert refs["network"].is_optional is True

    def test_no_markers(self):
        """Test class with no Annotated markers."""

        @dataclass
        class PlainClass:
            name: str
            count: int

        refs = get_refs(PlainClass)
        assert len(refs) == 0

    def test_multiple_markers(self):
        """Test class with multiple markers."""

        class Network:
            pass

        class Role:
            pass

        @dataclass
        class Resource:
            network: Annotated[Network, Ref()]
            role_arn: Annotated[str, Attr(Role, "Arn")]
            region: Annotated[str, ContextRef("region")]

        refs = get_refs(Resource)
        assert len(refs) == 3
        assert "network" in refs
        assert "role_arn" in refs
        assert "region" in refs


class TestGetDependencies:
    """Tests for get_dependencies function."""

    def test_ref_creates_dependency(self):
        """Test Ref marker creates dependency."""

        class Network:
            pass

        @dataclass
        class Subnet:
            network: Annotated[Network, Ref()]

        deps = get_dependencies(Subnet)
        assert Network in deps

    def test_attr_creates_dependency(self):
        """Test Attr marker creates dependency."""

        class Role:
            pass

        @dataclass
        class Function:
            role_arn: Annotated[str, Attr(Role, "Arn")]

        deps = get_dependencies(Function)
        assert Role in deps

    def test_reflist_creates_dependency(self):
        """Test RefList marker creates dependency."""

        class SecurityGroup:
            pass

        @dataclass
        class Instance:
            security_groups: Annotated[list[SecurityGroup], RefList()]

        deps = get_dependencies(Instance)
        assert SecurityGroup in deps

    def test_refdict_creates_dependency(self):
        """Test RefDict marker creates dependency."""

        class Endpoint:
            pass

        @dataclass
        class Service:
            routes: Annotated[dict[str, Endpoint], RefDict()]

        deps = get_dependencies(Service)
        assert Endpoint in deps

    def test_context_ref_no_dependency(self):
        """Test ContextRef does not create dependency."""

        @dataclass
        class Resource:
            region: Annotated[str, ContextRef("region")]

        deps = get_dependencies(Resource)
        assert len(deps) == 0

    def test_no_dependencies(self):
        """Test class with no dependencies."""

        @dataclass
        class Standalone:
            name: str = "test"

        deps = get_dependencies(Standalone)
        assert len(deps) == 0

    def test_multiple_dependencies(self):
        """Test class with multiple dependencies."""

        class Network:
            pass

        class Role:
            pass

        class SecurityGroup:
            pass

        @dataclass
        class Instance:
            network: Annotated[Network, Ref()]
            role_arn: Annotated[str, Attr(Role, "Arn")]
            sg: Annotated[SecurityGroup, Ref()]

        deps = get_dependencies(Instance)
        assert Network in deps
        assert Role in deps
        assert SecurityGroup in deps

    def test_transitive_dependencies(self):
        """Test transitive dependency resolution."""

        @dataclass
        class Level1:
            pass

        @dataclass
        class Level2:
            dep: Annotated[Level1, Ref()]

        @dataclass
        class Level3:
            dep: Annotated[Level2, Ref()]

        # Direct dependencies only
        direct_deps = get_dependencies(Level3, transitive=False)
        assert Level2 in direct_deps
        assert Level1 not in direct_deps

        # Transitive dependencies
        all_deps = get_dependencies(Level3, transitive=True)
        assert Level2 in all_deps
        assert Level1 in all_deps


class TestRefInfo:
    """Tests for RefInfo dataclass."""

    def test_create_ref_info(self):
        """Test creating RefInfo."""

        class Target:
            pass

        info = RefInfo(field="network", target=Target)
        assert info.field == "network"
        assert info.target is Target
        assert info.attr is None
        assert info.is_list is False
        assert info.is_dict is False
        assert info.is_optional is False
        assert info.is_context is False

    def test_create_attr_ref_info(self):
        """Test creating RefInfo for attribute reference."""

        class Target:
            pass

        info = RefInfo(field="role_arn", target=Target, attr="Arn")
        assert info.field == "role_arn"
        assert info.target is Target
        assert info.attr == "Arn"

    def test_create_list_ref_info(self):
        """Test creating RefInfo for list reference."""

        class Target:
            pass

        info = RefInfo(field="items", target=Target, is_list=True)
        assert info.is_list is True

    def test_create_optional_ref_info(self):
        """Test creating RefInfo for optional reference."""

        class Target:
            pass

        info = RefInfo(field="maybe", target=Target, is_optional=True)
        assert info.is_optional is True
