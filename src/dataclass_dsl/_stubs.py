"""
Stub file generator for IDE type checking.

Generates .pyi files so IDEs can understand dynamic imports from
setup_resources(). Works with Pylance, mypy, and other type checkers.

The `from . import *` pattern requires stub files for IDE autocomplete
because static analyzers can't see dynamic exports from setup_resources().

Usage:
    from dataclass_dsl import generate_stub_file, StubConfig

    config = StubConfig(
        package_name="mypackage",
        core_imports=["my_decorator", "MyResource", ...],
        expand_star_imports={"mypackage": [...names...]},
    )
    generate_stub_file(package_path, all_names, module_classes, config=config)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

__all__ = [
    "StubConfig",
    "generate_stub_file",
    "find_class_definitions",
    "expand_star_import",
    "extract_import_names",
    "is_resource_package",
    "find_resource_packages",
    "generate_stubs_for_path",
    "regenerate_stubs_for_path",
]


@dataclass
class StubConfig:
    """Configuration for domain-specific stub generation.

    Domain packages provide this to customize how stubs are generated
    for their specific package structure and imports. This enables IDE
    autocomplete for packages using the `from . import *` pattern with
    setup_resources().

    Attributes:
        package_name: The domain package name (e.g., "mypackage").
        core_imports: Names that should be available from the domain package.
        expand_star_imports: Map of module -> names for expanding star imports.
        extra_header_lines: Additional lines to add to stub header.

    Example:
        >>> config = StubConfig(
        ...     package_name="mypackage",
        ...     core_imports=["refs", "Object1", "Object2", "Object3"],
        ...     expand_star_imports={
        ...         "mypackage": ["refs", "Object1", "Object2", "Object3"],
        ...     },
        ... )
    """

    package_name: str = ""
    core_imports: list[str] = field(default_factory=list)
    expand_star_imports: dict[str, list[str]] = field(default_factory=dict)
    extra_header_lines: list[str] = field(default_factory=list)


# Exports from dataclass-dsl (for star import expansion)
DATACLASS_DSL_EXPORTS = [
    # Runtime markers
    "AttrRef",
    # Metaclass
    "RefMeta",
    # Decorator factory
    "create_decorator",
    # Registry
    "ResourceRegistry",
    # Ordering utilities
    "get_all_dependencies",
    "topological_sort",
    "get_creation_order",
    "get_deletion_order",
    "detect_cycles",
    "get_dependency_graph",
    # Provider
    "Provider",
    # Template
    "Template",
    # Loader
    "setup_resources",
    "find_refs_in_source",
    "find_class_definitions",
    # Stubs
    "StubConfig",
    "generate_stub_file",
    "find_resource_packages",
    "generate_stubs_for_path",
    # Helpers
    "is_attr_ref",
    "is_class_ref",
    "get_ref_target",
    "apply_metaclass",
    # Type markers (Annotated-based)
    "Ref",
    "Attr",
    "RefList",
    "RefDict",
    "ContextRef",
    "RefInfo",
    "get_refs",
    "get_dependencies",
]


def find_class_definitions(source: str) -> list[str]:
    """Extract class names defined in a source file.

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


def _extract_relative_module_name(import_line: str) -> str | None:
    """Extract module name from a relative star import.

    Args:
        import_line: An import statement like "from .params import *".

    Returns:
        Module name (e.g., "params") or None if not a relative star import.

    Example:
        >>> _extract_relative_module_name("from .params import *  # noqa")
        'params'
        >>> _extract_relative_module_name("from .main import *")
        'main'
        >>> _extract_relative_module_name("from wetwire_aws import *")
        None
    """
    clean_line = import_line
    if "#" in clean_line:
        clean_line = clean_line.split("#")[0].strip()

    # Match "from .module import *" pattern
    match = re.match(r"from\s+\.(\w+)\s+import\s+\*", clean_line)
    if match:
        return match.group(1)
    return None


def expand_star_import(
    import_line: str,
    config: StubConfig | None = None,
) -> tuple[str, list[str]]:
    """Expand a star import to explicit imports if from a known module.

    For known modules (like dataclass_dsl), expands `from x import *`
    to explicit imports so Pylance can resolve them.

    Args:
        import_line: An import statement line.
        config: Optional domain-specific stub configuration.

    Returns:
        Tuple of (expanded_import_line, list_of_names).
        If not a star import or unknown module, returns original line
        with empty list.

    Example:
        >>> line = "from dataclass_dsl import *"
        >>> expanded, names = expand_star_import(line)
        >>> "AttrRef" in names
        True
    """
    clean_line = import_line
    if "#" in clean_line:
        clean_line = clean_line.split("#")[0].strip()

    # Check dataclass-dsl core
    if "from dataclass_dsl import *" in clean_line:
        names = sorted(DATACLASS_DSL_EXPORTS)
        expanded = f"from dataclass_dsl import {', '.join(names)}"
        return expanded, names

    # Check domain-specific expansions
    if config:
        for pattern, names in config.expand_star_imports.items():
            if f"from {pattern} import *" in clean_line:
                sorted_names = sorted(names)
                expanded = f"from {pattern} import {', '.join(sorted_names)}"
                return expanded, sorted_names

    return import_line, []


def extract_import_names(import_stmt: str) -> list[str]:
    """Extract imported names from an import statement.

    Handles:
    - from x import a, b, c
    - from x import (a, b, c)
    - from x import a as alias
    - from x import *  (returns empty list - star imports handled separately)
    - import x, y, z
    - Comments like # noqa: F403 are stripped

    Args:
        import_stmt: An import statement string.

    Returns:
        List of imported names.

    Example:
        >>> extract_import_names("from foo import bar, baz")
        ['bar', 'baz']
        >>> extract_import_names("from foo import bar as b")
        ['b']
    """
    names: list[str] = []

    # Remove newlines and extra whitespace
    import_stmt = " ".join(import_stmt.split())

    # Strip trailing comments (e.g., noqa directives)
    if "#" in import_stmt:
        import_stmt = import_stmt.split("#")[0].strip()

    if import_stmt.startswith("from "):
        # from x import a, b, c  OR  from x import (a, b, c)
        if " import " in import_stmt:
            imports_part = import_stmt.split(" import ", 1)[1]
            # Remove parentheses
            imports_part = imports_part.replace("(", "").replace(")", "")

            # Handle star imports - return empty (caller handles these specially)
            if imports_part.strip() == "*":
                return []

            # Split by comma
            for item in imports_part.split(","):
                item = item.strip()
                if " as " in item:
                    # from x import a as b -> use 'b'
                    names.append(item.split(" as ")[1].strip())
                elif item and item != "*":
                    names.append(item)
    elif import_stmt.startswith("import "):
        # import x, y, z
        imports_part = import_stmt[7:]  # Remove "import "
        for item in imports_part.split(","):
            item = item.strip()
            if " as " in item:
                names.append(item.split(" as ")[1].strip())
            elif item:
                # For 'import x.y.z', the available name is 'x'
                names.append(item.split(".")[0])

    return names


def generate_stub_file(
    package_path: Path,
    all_names: list[str] | None = None,
    module_classes: dict[str, list[str]] | None = None,
    *,
    config: StubConfig | None = None,
) -> bool:
    """Generate .pyi stub file for IDE type checking.

    This allows IDEs like VSCode/Pylance to understand what names are
    exported from resource packages, even though they're loaded dynamically.

    Args:
        package_path: Path to the package directory.
        all_names: Optional list of all exported names.
        module_classes: Optional dict of module -> class names.
        config: Optional domain-specific configuration.

    Returns:
        True if stubs were generated/updated, False if unchanged.

    Example:
        >>> from pathlib import Path
        >>> generate_stub_file(Path("mypackage/resources"))
        True
    """
    if module_classes is None:
        module_classes = {}
        for file in package_path.glob("*.py"):
            if file.name.startswith("_"):
                continue
            source = file.read_text()
            module_name = file.stem
            module_classes[module_name] = find_class_definitions(source)

    if all_names is None:
        all_names = []
        for classes in module_classes.values():
            all_names.extend(classes)

    # Build stub content
    init_stub_path = package_path / "__init__.pyi"
    init_lines = ['"""Auto-generated stub for IDE type checking."""', ""]

    # Read __init__.py to extract and process imports
    init_file = package_path / "__init__.py"
    imported_names: list[str] = []

    # Add extra header lines from config and extract imported names
    if config and config.extra_header_lines:
        init_lines.extend(config.extra_header_lines)
        init_lines.append("")
    # Use core_imports from config - these are all the names that should be in __all__
    if config and config.core_imports:
        imported_names.extend(config.core_imports)

    if init_file.exists():
        init_source = init_file.read_text()
        in_import = False
        import_buffer: list[str] = []

        for line in init_source.splitlines():
            # Skip setup_resources call and comments
            if "setup_resources(" in line or line.strip().startswith("#"):
                continue

            if in_import:
                import_buffer.append(line)
                if ")" in line:
                    # End of multi-line import
                    full_import = "\n".join(import_buffer)
                    init_lines.append(full_import)
                    imported_names.extend(extract_import_names(full_import))
                    import_buffer = []
                    in_import = False
            elif line.startswith("from ") or line.startswith("import "):
                if "(" in line and ")" not in line:
                    # Start of multi-line import
                    in_import = True
                    import_buffer = [line]
                else:
                    # Check for relative star imports (e.g., "from .params import *")
                    relative_module = _extract_relative_module_name(line)
                    if relative_module:
                        # Read the local module file and extract class names
                        module_file = package_path / f"{relative_module}.py"
                        if module_file.exists():
                            module_source = module_file.read_text()
                            class_names = find_class_definitions(module_source)
                            # Add to module_classes for re-export generation
                            if relative_module not in module_classes:
                                module_classes[relative_module] = []
                            for cls in class_names:
                                if cls not in module_classes[relative_module]:
                                    module_classes[relative_module].append(cls)
                            # Don't add star import to stub - will be explicit
                            continue

                    # Try to expand star imports from known modules
                    expanded_line, star_names = expand_star_import(line, config)
                    init_lines.append(expanded_line)
                    if star_names:
                        imported_names.extend(star_names)
                    else:
                        imported_names.extend(extract_import_names(line))

    init_lines.append("")

    # Re-export all classes from resource modules
    all_resource_classes: list[str] = []
    for mod_name, classes in sorted(module_classes.items()):
        if classes:
            for cls in sorted(classes):
                init_lines.append(f"from .{mod_name} import {cls} as {cls}")
                all_resource_classes.append(cls)

    init_lines.append("")

    # Build __all__ for star imports - Pylance needs this to resolve imports
    all_exports = imported_names + all_resource_classes
    init_lines.append(f"__all__: list[str] = {sorted(set(all_exports))!r}")
    init_lines.append("")

    return _write_stub_if_changed(init_stub_path, "\n".join(init_lines))


def _write_stub_if_changed(stub_path: Path, content: str) -> bool:
    """Write stub file only if content has changed.

    Args:
        stub_path: Path to the stub file.
        content: Content to write.

    Returns:
        True if file was written, False if unchanged.
    """
    try:
        existing = stub_path.read_text()
        if existing == content:
            return False
    except FileNotFoundError:
        pass

    stub_path.write_text(content)
    return True


def is_resource_package(path: Path) -> bool:
    """Check if a directory is a resource package using setup_resources().

    A resource package has __init__.py that calls setup_resources().

    Args:
        path: Directory path to check.

    Returns:
        True if the directory is a resource package.

    Example:
        >>> from pathlib import Path
        >>> is_resource_package(Path("myproject/resources"))
        True
    """
    init_file = path / "__init__.py"
    if not init_file.exists():
        return False

    content = init_file.read_text()
    return "setup_resources(" in content


def find_resource_packages(root: Path) -> list[Path]:
    """Find all resource packages under a root directory.

    Looks for directories with __init__.py that contain setup_resources().

    Args:
        root: Root directory to search.

    Returns:
        List of paths to resource packages.

    Example:
        >>> from pathlib import Path
        >>> packages = find_resource_packages(Path("myproject"))
        >>> len(packages) >= 0
        True
    """
    packages: list[Path] = []

    for init_file in root.rglob("__init__.py"):
        package_dir = init_file.parent
        if is_resource_package(package_dir):
            packages.append(package_dir)

    return packages


def generate_stubs_for_path(
    path: Path,
    config: StubConfig | None = None,
) -> int:
    """Generate stubs for all resource packages under a path.

    Args:
        path: Directory to scan for resource packages.
        config: Optional domain-specific configuration.

    Returns:
        Number of resource packages processed.

    Example:
        >>> from pathlib import Path
        >>> count = generate_stubs_for_path(Path("myproject"))
        >>> count >= 0
        True
    """
    path = path.resolve()

    if is_resource_package(path):
        packages = [path]
    else:
        packages = find_resource_packages(path)

    for package_path in packages:
        generate_stub_file(package_path, config=config)

    return len(packages)


def regenerate_stubs_for_path(
    path: Path,
    config: StubConfig,
    verbose: bool = False,
) -> int:
    """Regenerate stubs for resource packages after code changes.

    This is designed for use after lint fixes - it scans for packages
    using setup_resources() and regenerates their stubs.

    Args:
        path: Directory or file path to scan.
        config: Domain-specific stub configuration.
        verbose: If True, print regeneration info.

    Returns:
        Number of packages that had stubs regenerated.

    Example:
        >>> from pathlib import Path
        >>> from mypackage import MY_STUB_CONFIG
        >>> count = regenerate_stubs_for_path(Path("myproject"), MY_STUB_CONFIG)
        >>> count >= 0
        True
    """
    import ast

    path = Path(path).resolve()
    count = 0

    # Find all __init__.py files
    if path.is_file():
        init_files = [path] if path.name == "__init__.py" else []
    else:
        init_files = list(path.rglob("__init__.py"))

    for init_file in init_files:
        try:
            content = init_file.read_text()
            if "setup_resources" not in content:
                continue

            # Parse to find exported classes
            pkg_dir = init_file.parent
            py_files = [f for f in pkg_dir.glob("*.py") if not f.name.startswith("_")]

            # Extract class names from each file
            all_names: list[str] = []
            module_classes: dict[str, list[str]] = {}

            for py_file in py_files:
                try:
                    source = py_file.read_text()
                    tree = ast.parse(source)
                    classes = []
                    for node in ast.walk(tree):
                        if isinstance(node, ast.ClassDef):
                            classes.append(node.name)
                            all_names.append(node.name)
                    if classes:
                        module_classes[py_file.stem] = classes
                except Exception:
                    continue

            if all_names:
                generate_stub_file(pkg_dir, all_names, module_classes, config=config)
                count += 1
                if verbose:
                    print(f"Regenerated stubs: {pkg_dir}")

        except Exception as e:
            if verbose:
                print(f"Error regenerating stubs for {init_file}: {e}")

    return count
