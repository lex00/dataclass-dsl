"""
Resource loader with topological import ordering.

This module provides setup_resources() which enables the `from . import *`
pattern for multi-file packages:

1. Discovers Python files in a package directory
2. Parses them to find class definitions and reference annotations
3. Builds a dependency graph from Ref[T], Attr[T, ...] and no-parens patterns
4. Imports modules in topological order
5. Injects already-loaded classes into each module's namespace
6. Generates .pyi stubs for IDE support

Usage in a resources package __init__.py:
    from dataclass_dsl import setup_resources, StubConfig

    stub_config = StubConfig(
        package_name="mypackage",
        core_imports=["Object1", "Object2", "Object3"],
    )
    setup_resources(__file__, __name__, globals(), stub_config=stub_config)
"""

from __future__ import annotations

import importlib.util
import re
import sys
from collections.abc import Callable
from pathlib import Path
from types import ModuleType
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from dataclass_dsl._stubs import StubConfig

__all__ = [
    "setup_resources",
    "find_refs_in_source",
    "find_class_definitions",
    "_AttributePlaceholder",
    "_ClassPlaceholder",
]


class _AttributePlaceholder:
    """Placeholder for an attribute access on a class placeholder.

    When a placeholder class is accessed with an attribute (e.g., MyRole.Arn),
    this object stores both the class name and attribute name for later resolution.

    Example:
        MyRole = _ClassPlaceholder("MyRole", "mypackage.roles")
        arn = MyRole.Arn  # Returns _AttributePlaceholder(...)

    After all modules are loaded, _resolve_value() converts this to a real
    attribute access or GetAtt call depending on the domain.
    """

    __slots__ = ("_class_name", "_attr_name", "_module")

    def __init__(self, class_name: str, attr_name: str, module: str):
        self._class_name = class_name
        self._attr_name = attr_name
        self._module = module

    def __repr__(self) -> str:
        return f"<AttributePlaceholder {self._class_name}.{self._attr_name}>"

    def __hash__(self) -> int:
        return hash((self._class_name, self._attr_name, self._module))

    def __eq__(self, other: object) -> bool:
        if isinstance(other, _AttributePlaceholder):
            return (
                self._class_name == other._class_name
                and self._attr_name == other._attr_name
                and self._module == other._module
            )
        return False

    def __getattr__(self, attr: str) -> _AttributePlaceholder:
        """Support chained attribute access like MyDB.Endpoint.Address."""
        if attr.startswith("_"):
            raise AttributeError(attr)
        # Chain: MyDB.Endpoint.Address -> ("MyDB", "Endpoint.Address")
        return _AttributePlaceholder(
            self._class_name, f"{self._attr_name}.{attr}", self._module
        )


class _ClassPlaceholder:
    """Placeholder for a class defined later in the same file or in a cycle.

    When setup_resources() loads a module, it injects placeholders for:
    1. Classes defined in the same file (forward references)
    2. Classes from other files that haven't loaded yet (circular dependencies)

    This allows bare class names to work with forward references:

        @decorator
        class A:
            b_ref = B  # B is a placeholder here, resolved after module executes

        @decorator
        class B:
            pass

    Attribute access is also supported for GetAtt-style patterns:

        @decorator
        class MyFunction:
            role_arn = MyRole.Arn  # Returns _AttributePlaceholder

    After the module executes, _resolve_placeholders() walks all classes
    and replaces placeholder references with the real classes.
    """

    __slots__ = ("_name", "_module")

    def __init__(self, name: str, module: str):
        self._name = name
        self._module = module

    def __repr__(self) -> str:
        return f"<Placeholder for {self._module}.{self._name}>"

    def __hash__(self) -> int:
        return hash((self._name, self._module))

    def __eq__(self, other: object) -> bool:
        if isinstance(other, _ClassPlaceholder):
            return self._name == other._name and self._module == other._module
        return False

    def __getattr__(self, attr: str) -> _AttributePlaceholder:
        """Support attribute access like MyRole.Arn on placeholders.

        This enables no-parens patterns for GetAtt-style references:
            role_arn = MyRole.Arn  # Works even if MyRole is a placeholder
        """
        if attr.startswith("_"):
            raise AttributeError(attr)
        return _AttributePlaceholder(self._name, attr, self._module)


def find_refs_in_source(source: str) -> set[str]:
    """
    Extract class names from reference patterns.

    Matches patterns used for references:

    Type annotation patterns:
    - Ref[ClassName]
    - Attr[ClassName, ...]
    - RefList[ClassName]
    - RefDict[..., ClassName]

    No-parens patterns (value assignments):
    - ClassName.Attribute (e.g., Object1.Id)
    - = ClassName  (direct class reference, e.g., parent = Object1)

    Function call patterns (for domain-specific helpers):
    - ref(ClassName) - reference helper function
    - get_att(ClassName, ...) - attribute helper function

    Args:
        source: Python source code text.

    Returns:
        Set of class names referenced in patterns.

    Example:
        >>> source = '''
        ... class Object2:
        ...     parent: Ref[Object1]
        ...     parent_id = Object1.Id
        ... '''
        >>> find_refs_in_source(source)
        {'Object1'}
    """
    refs: set[str] = set()

    # Match Ref[ClassName]
    for match in re.finditer(r"\bRef\[([A-Za-z_]\w*)\]", source):
        refs.add(match.group(1))

    # Match Attr[ClassName, ...] - class name is first type argument
    for match in re.finditer(r"\bAttr\[([A-Za-z_]\w*)\s*,", source):
        refs.add(match.group(1))

    # Match RefList[ClassName]
    for match in re.finditer(r"\bRefList\[([A-Za-z_]\w*)\]", source):
        refs.add(match.group(1))

    # Match RefDict[..., ClassName] - class name is second type argument
    for match in re.finditer(r"\bRefDict\[[^,]+,\s*([A-Za-z_]\w*)\]", source):
        refs.add(match.group(1))

    # Match no-parens attribute pattern: ClassName.Attribute
    # e.g., parent_id = Object1.Id
    # Must be PascalCase to avoid matching module.function patterns
    for match in re.finditer(r"\b([A-Z][A-Za-z0-9]*)\.[A-Z][A-Za-z0-9]*\b", source):
        refs.add(match.group(1))

    # Match no-parens class reference: = ClassName (at end of line or before comment)
    # e.g., parent = Object1, value = myDynamoDBTable
    # Match identifiers with at least one uppercase letter (PascalCase or camelCase)
    # to avoid matching = some_variable (all lowercase with underscores)
    for match in re.finditer(
        r"=\s+([a-zA-Z][A-Za-z0-9]*)\s*(?:#|$)", source, re.MULTILINE
    ):
        name = match.group(1)
        # Require at least one uppercase letter to distinguish from snake_case vars
        if any(c.isupper() for c in name):
            refs.add(name)

    # Match class names inside lists: [ClassName, ...] or [ClassName]
    # e.g., security_group_ids = [EC2InstanceSG, ALBExternalAccessSG]
    # Match identifiers with at least one uppercase letter (PascalCase or camelCase)
    for match in re.finditer(r"\[\s*([a-zA-Z][A-Za-z0-9]*)\b", source):
        name = match.group(1)
        if any(c.isupper() for c in name):
            refs.add(name)
    for match in re.finditer(r",\s*([a-zA-Z][A-Za-z0-9]*)\s*[\],]", source):
        name = match.group(1)
        if any(c.isupper() for c in name):
            refs.add(name)

    # Match ref(ClassName) - reference helper function
    # Matches identifiers (not quoted strings like ref("X"))
    for match in re.finditer(r"\bref\(([A-Za-z_]\w*)\)", source):
        refs.add(match.group(1))

    # Match get_att(ClassName, ...) - attribute helper function
    for match in re.finditer(r"\bget_att\(([A-Za-z_]\w*)\s*,", source):
        refs.add(match.group(1))

    # Match class names as function arguments: Func(ClassName), Func(arg, ClassName)
    # e.g., Split('/', ASCPrivateLinkCertificate)
    # Match identifier after (, or , that has at least one uppercase letter
    for match in re.finditer(r"[,(]\s*([a-zA-Z][A-Za-z0-9]*)\s*[,)]", source):
        name = match.group(1)
        # Require at least one uppercase letter to distinguish from variables
        if any(c.isupper() for c in name):
            refs.add(name)

    # Match class names as dict values: 'key': ClassName or "key": ClassName
    # e.g., {'awslogs-group': CloudwatchLogsGroup, ...}
    dict_value_pattern = r"['\"][\w-]+['\"]\s*:\s*([a-zA-Z][A-Za-z0-9]*)\b"
    for match in re.finditer(dict_value_pattern, source):
        name = match.group(1)
        # Require at least one uppercase letter to distinguish from variables
        if any(c.isupper() for c in name):
            refs.add(name)

    return refs


def find_class_definitions(source: str) -> list[str]:
    """
    Extract class names defined in a source file.

    Args:
        source: Python source code text.

    Returns:
        List of class names found in the source.

    Example:
        >>> source = '''
        ... class Object1:
        ...     pass
        ...
        ... class Object2:
        ...     pass
        ... '''
        >>> find_class_definitions(source)
        ['Object1', 'Object2']
    """
    return re.findall(r"^class\s+(\w+)", source, re.MULTILINE)


def _resolve_value(value: Any, class_map: dict[str, type]) -> Any:
    """Recursively resolve placeholders in a value.

    Args:
        value: The value to resolve (may contain placeholders).
        class_map: Mapping from class name to real class.

    Returns:
        The value with placeholders replaced by real classes.
    """
    if isinstance(value, _ClassPlaceholder):
        return class_map.get(value._name, value)

    if isinstance(value, _AttributePlaceholder):
        # Resolve attribute placeholders like MyRole.Arn
        real_class = class_map.get(value._class_name)
        if real_class is not None:
            # Walk the attribute chain: "Endpoint.Address" -> ["Endpoint", "Address"]
            result = real_class
            for attr_part in value._attr_name.split("."):
                result = getattr(result, attr_part)
            return result
        # Can't resolve yet - return as-is
        return value

    if isinstance(value, list):
        return [_resolve_value(v, class_map) for v in value]

    if isinstance(value, tuple):
        return tuple(_resolve_value(v, class_map) for v in value)

    if isinstance(value, dict):
        return {k: _resolve_value(v, class_map) for k, v in value.items()}

    # Check if the value has a callable _resolve_placeholders method (e.g., intrinsics)
    resolver = getattr(value, "_resolve_placeholders", None)
    if resolver is not None and callable(resolver):
        return resolver(class_map)

    return value


def _resolve_class_placeholders(cls: type, class_map: dict[str, type]) -> None:
    """Resolve placeholder references in a class's attributes.

    This walks the class's __dict__ and replaces any _ClassPlaceholder
    instances with the real classes from class_map.

    Args:
        cls: The class to resolve placeholders in.
        class_map: Mapping from class name to real class.
    """
    # Get class annotations for type hints (we don't modify these)
    # We focus on class attributes (field defaults, etc.)

    for attr_name in list(vars(cls)):
        if attr_name.startswith("_"):
            continue

        try:
            value = getattr(cls, attr_name)
        except AttributeError:
            continue

        # Skip methods, properties, and class methods
        if callable(value) and not isinstance(value, type):
            continue
        if isinstance(value, (property, classmethod, staticmethod)):
            continue

        resolved = _resolve_value(value, class_map)
        if resolved is not value:
            try:
                setattr(cls, attr_name, resolved)
            except (AttributeError, TypeError):
                # Some attributes can't be set (e.g., __dict__)
                pass


def _resolve_module_placeholders(
    module: ModuleType,
    local_class_names: list[str],
) -> None:
    """Resolve placeholders in all classes defined in a module.

    After a module executes, this function:
    1. Builds a map of class names to real classes
    2. Walks each class and resolves placeholder references

    Args:
        module: The module that was just executed.
        local_class_names: List of class names defined in this module.
    """
    # Build map of real classes (those that are actually types, not placeholders)
    class_map: dict[str, type] = {}
    for name in local_class_names:
        obj = getattr(module, name, None)
        if isinstance(obj, type):
            class_map[name] = obj

    # Resolve placeholders in each class
    for cls in class_map.values():
        _resolve_class_placeholders(cls, class_map)


def _topological_sort(deps: dict[str, set[str]]) -> list[str]:
    """
    Kahn's algorithm for topological sort with cycle handling.

    Args:
        deps: Dict mapping module name to set of module names it depends on.

    Returns:
        List of module names in dependency order (dependencies first).
        Handles cycles by breaking them and continuing the sort.
    """
    # Make a mutable copy of deps
    remaining_deps: dict[str, set[str]] = {m: set(d) for m, d in deps.items()}

    result: list[str] = []

    while remaining_deps:
        # Find modules with no remaining dependencies
        ready = [m for m, d in remaining_deps.items() if len(d) == 0]

        if ready:
            # Process modules with no dependencies
            for m in sorted(ready):  # Sort for determinism
                result.append(m)
                del remaining_deps[m]
                # Remove this module from others' dependency sets
                for other_deps in remaining_deps.values():
                    other_deps.discard(m)
        else:
            # All remaining modules have dependencies -> there's a cycle
            # Find the module that is depended upon by most other remaining
            # modules - this breaks the cycle at a "hub" node
            dep_count: dict[str, int] = dict.fromkeys(remaining_deps, 0)
            for d in remaining_deps.values():
                for dep in d:
                    if dep in dep_count:
                        dep_count[dep] += 1

            # Pick the most-depended-upon module, with alphabetical tiebreaker
            cycle_breaker = max(
                remaining_deps.keys(),
                key=lambda m: (dep_count[m], -ord(m[0]) if m else 0, m),
            )
            result.append(cycle_breaker)
            del remaining_deps[cycle_breaker]
            # Remove this module from others' dependency sets
            for other_deps in remaining_deps.values():
                other_deps.discard(cycle_breaker)

    return result


def _apply_metaclass_to_resource_classes(
    module: ModuleType,
    resource_field: str = "resource",
) -> None:
    """Apply RefMeta to classes with resource annotation in this module.

    This enables the no-parens `.Arn` pattern to work during module loading,
    before full decoration is applied. Must be called immediately after
    module execution so that subsequently-loaded modules can use `.Arn`
    on classes from this module.

    Classes that already have RefMeta as their metaclass are skipped.

    Args:
        module: The just-executed module to scan.
        resource_field: Field name that identifies resource classes.
    """
    from dataclass_dsl._metaclass import RefMeta
    from dataclass_dsl._utils import apply_metaclass

    for name in dir(module):
        if name.startswith("_"):
            continue
        obj = getattr(module, name, None)
        if not isinstance(obj, type):
            continue
        # Skip if already has RefMeta (already decorated)
        if isinstance(obj, RefMeta):
            continue
        # Check for resource annotation
        annotations = getattr(obj, "__annotations__", {})
        if resource_field not in annotations:
            continue
        # Apply metaclass in place
        new_cls: type = apply_metaclass(obj, RefMeta)
        setattr(module, name, new_cls)


def _make_metaclass_applying_build_class(
    resource_field: str = "resource",
) -> Callable[..., type]:
    """Create a __build_class__ wrapper that applies RefMeta to resource classes.

    This enables the invisible decorator pattern for within-file forward refs.
    When a class with a `resource:` annotation is defined, RefMeta is applied
    immediately, so subsequent class definitions in the same file can use
    `.Arn` on the class.

    Example:
        class MyRole:
            resource: iam.Role
            role_name = "my-role"

        class MyFunction:
            resource: lambda_.Function
            role = MyRole.Arn  # This works because MyRole already has RefMeta

    Returns:
        A callable that wraps the original __build_class__.
    """
    import builtins

    original_build_class = builtins.__build_class__

    def metaclass_applying_build_class(
        func: Callable[..., None], name: str, *bases: type, **kwargs: Any
    ) -> type:
        # First, build the class normally
        cls: type = original_build_class(func, name, *bases, **kwargs)

        # Check if this is a resource class that needs RefMeta
        annotations = getattr(cls, "__annotations__", {})
        if resource_field in annotations:
            # Import here to avoid circular imports
            from dataclass_dsl._metaclass import RefMeta

            # Skip if already has RefMeta
            if not isinstance(cls, RefMeta):
                from dataclass_dsl._utils import apply_metaclass

                cls = apply_metaclass(cls, RefMeta)

        return cls

    return metaclass_applying_build_class


def _load_module_with_namespace(
    mod_name: str,
    full_mod_name: str,
    pkg_path: Path,
    namespace: dict[str, Any],
    local_class_names: list[str] | None = None,
    cross_file_refs: set[str] | None = None,
) -> ModuleType:
    """
    Load a module, injecting namespace and placeholders before execution.

    This allows Ref[ClassName] and no-parens patterns to resolve
    during class body evaluation:
    - Classes from other files: injected from namespace
    - Classes from this file (forward refs): injected as placeholders
    - Classes from other files not yet loaded (cycles): injected as placeholders

    After execution, local placeholders are resolved. Cross-file placeholders
    are resolved after all modules are loaded (in setup_resources).

    Args:
        mod_name: Short module name (e.g., "object1").
        full_mod_name: Full module name (e.g., "mypackage.objects.object1").
        pkg_path: Path to the package directory.
        namespace: Shared namespace with already-loaded classes.
        local_class_names: Class names defined in this module (for placeholders).
        cross_file_refs: Class names this module references from other files.
            Used to inject placeholders for cross-file deps in cycles.

    Returns:
        The loaded module.
    """
    file_path = pkg_path / f"{mod_name}.py"

    # Create module spec
    spec = importlib.util.spec_from_file_location(full_mod_name, file_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load module {full_mod_name} from {file_path}")

    # Create module object
    module = importlib.util.module_from_spec(spec)

    # Inject shared namespace BEFORE execution
    # This makes sibling classes available during class body evaluation
    for name, obj in namespace.items():
        setattr(module, name, obj)

    # Inject placeholders for local classes not yet in namespace
    # This enables forward references within the same file
    if local_class_names:
        for cls_name in local_class_names:
            if cls_name not in namespace:
                placeholder = _ClassPlaceholder(cls_name, full_mod_name)
                setattr(module, cls_name, placeholder)

    # Inject placeholders for cross-file refs not yet in namespace (cycles)
    # This enables bare class names like MyRole.Arn even when there's a cycle
    if cross_file_refs:
        for cls_name in cross_file_refs:
            if cls_name not in namespace:
                placeholder = _ClassPlaceholder(cls_name, full_mod_name)
                setattr(module, cls_name, placeholder)

    # Register in sys.modules before execution (standard Python behavior)
    sys.modules[full_mod_name] = module

    # Install custom __build_class__ that applies RefMeta immediately when a
    # class with resource annotation is defined. This enables within-file
    # forward references like: role = MyRole.Arn (where MyRole is defined above)
    import builtins

    original_build_class = builtins.__build_class__
    builtins.__build_class__ = _make_metaclass_applying_build_class()

    try:
        # Execute the module code
        spec.loader.exec_module(module)
    finally:
        # Always restore the original __build_class__
        builtins.__build_class__ = original_build_class

    # Note: We no longer need _apply_metaclass_to_resource_classes() here
    # because RefMeta is now applied immediately during class creation

    # Resolve local placeholders now that all local classes are defined
    # Cross-file placeholders are resolved after ALL modules are loaded
    if local_class_names:
        _resolve_module_placeholders(module, local_class_names)

    return module


def setup_resources(
    init_file: str,
    package_name: str,
    package_globals: dict[str, Any],
    *,
    stub_config: StubConfig | None = None,
    generate_stubs: bool = True,
    extra_namespace: dict[str, Any] | None = None,
) -> None:
    """
    Set up resource imports with topological ordering for `from . import *`.

    This function:
    1. Finds all .py files in the package directory
    2. Parses them to find class definitions and Ref/Attr/no-parens patterns
    3. Builds a dependency graph from the patterns
    4. Imports modules in topological order
    5. Injects previously-loaded classes into each module's namespace
    6. Optionally generates .pyi stubs for IDE support

    Args:
        init_file: Path to __init__.py (__file__).
        package_name: Package name (__name__).
        package_globals: Package globals dict (globals()).
        stub_config: Optional stub generation configuration.
        generate_stubs: Whether to generate .pyi files (default: True).
        extra_namespace: Optional dict of names to inject into each module's
            namespace before execution. Useful for domain packages to inject
            decorators, type markers, and helper functions.

    Example:
        # In mypackage/objects/__init__.py
        from dataclass_dsl import setup_resources, StubConfig

        stub_config = StubConfig(
            package_name="mypackage",
            core_imports=["refs", "Object1", "Object2"],
        )
        setup_resources(__file__, __name__, globals(), stub_config=stub_config)
    """
    pkg_path = Path(init_file).parent

    # 1. Discover module files and their class definitions/references
    module_sources: dict[str, str] = {}
    module_classes: dict[str, list[str]] = {}

    for file in pkg_path.glob("*.py"):
        if file.name.startswith("_"):
            continue
        source = file.read_text()
        module_name = file.stem
        module_sources[module_name] = source
        module_classes[module_name] = find_class_definitions(source)

    # 2. Build class -> module map
    class_to_module: dict[str, str] = {}
    for mod, classes in module_classes.items():
        for cls in classes:
            class_to_module[cls] = mod

    # 3. Build dependency graph (module -> set of modules it depends on)
    # Also track which cross-file classes each module references
    deps: dict[str, set[str]] = {mod: set() for mod in module_sources}
    module_cross_file_refs: dict[str, set[str]] = {mod: set() for mod in module_sources}
    for mod, source in module_sources.items():
        for ref_class in find_refs_in_source(source):
            if ref_class in class_to_module:
                dep_mod = class_to_module[ref_class]
                if dep_mod != mod:
                    deps[mod].add(dep_mod)
                    module_cross_file_refs[mod].add(ref_class)

    # 4. Topological sort
    import_order = _topological_sort(deps)

    # 5. Import in order, injecting shared namespace BEFORE each module executes
    shared_namespace: dict[str, Any] = {}
    if extra_namespace:
        shared_namespace.update(extra_namespace)
    all_names: list[str] = []
    loaded_modules: list[ModuleType] = []

    for mod_name in import_order:
        full_mod_name = f"{package_name}.{mod_name}"

        # Skip if already imported (shouldn't happen with topological order)
        if full_mod_name in sys.modules:
            module = sys.modules[full_mod_name]
        else:
            # Load module with namespace injection BEFORE execution
            # Pass local class names for placeholder injection (forward refs)
            # Pass cross-file refs for placeholder injection (cycles)
            local_classes = module_classes.get(mod_name, [])
            cross_file_refs = module_cross_file_refs.get(mod_name, set())
            module = _load_module_with_namespace(
                mod_name,
                full_mod_name,
                pkg_path,
                shared_namespace,
                local_class_names=local_classes,
                cross_file_refs=cross_file_refs,
            )

        loaded_modules.append(module)

        # Extract classes from this module and add to shared namespace
        for cls_name in module_classes.get(mod_name, []):
            if hasattr(module, cls_name):
                obj = getattr(module, cls_name)
                shared_namespace[cls_name] = obj
                package_globals[cls_name] = obj
                all_names.append(cls_name)

    # 6. Final resolution pass for cross-file placeholders
    # Now that all modules are loaded, resolve any remaining placeholders
    # This handles circular dependencies where some placeholders couldn't
    # be resolved during initial module loading
    for module in loaded_modules:
        for cls_name in dir(module):
            if cls_name.startswith("_"):
                continue
            try:
                obj = getattr(module, cls_name)
            except AttributeError:
                continue
            if isinstance(obj, type):
                _resolve_class_placeholders(obj, shared_namespace)

    # 7. Set __all__ for star imports
    package_globals["__all__"] = all_names

    # 8. Generate stubs for IDE support
    if generate_stubs and stub_config is not None:
        from dataclass_dsl._stubs import generate_stub_file

        generate_stub_file(pkg_path, all_names, module_classes, config=stub_config)
