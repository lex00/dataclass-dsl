"""
CLI framework for dataclass-dsl domain packages.

Provides reusable CLI utilities for building domain-specific CLIs
like wetwire-aws, wetwire-gcp, etc.

Example:
    >>> from dataclass_dsl import ResourceRegistry
    >>> from dataclass_dsl._cli import (
    ...     discover_resources,
    ...     add_common_args,
    ...     create_list_command,
    ...     create_validate_command,
    ... )
    >>>
    >>> registry = ResourceRegistry()
    >>>
    >>> def get_resource_type(cls):
    ...     return getattr(cls, "resource_type", "Unknown")
    >>>
    >>> list_cmd = create_list_command(registry, get_resource_type)
"""

from __future__ import annotations

import argparse
import importlib
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from dataclass_dsl._registry import ResourceRegistry
    from dataclass_dsl._template import Template

__all__ = [
    "discover_resources",
    "add_common_args",
    "create_list_command",
    "create_validate_command",
    "create_build_command",
    "create_lint_command",
    "LintIssue",
]


def discover_resources(
    module_path: str,
    registry: ResourceRegistry,
    verbose: bool = False,
) -> int:
    """
    Import a module to trigger resource registration.

    When a module is imported, any decorated classes are automatically
    registered with the registry. This function imports the module and
    returns the count of newly registered resources.

    Args:
        module_path: Python module path to import (e.g., "myapp.infra")
        registry: The resource registry to count registrations
        verbose: If True, print discovery info to stderr

    Returns:
        Number of resources discovered (registered) from the import

    Raises:
        SystemExit: If the module cannot be imported
    """
    before = len(list(registry.get_all()))
    try:
        importlib.import_module(module_path)
    except ImportError as e:
        print(f"Error: Could not import module '{module_path}': {e}", file=sys.stderr)
        sys.exit(1)
    after = len(list(registry.get_all()))
    count = after - before
    if verbose:
        print(f"Discovered {count} resources from {module_path}", file=sys.stderr)
    return count


def add_common_args(parser: argparse.ArgumentParser) -> None:
    """
    Add common CLI arguments used by most commands.

    Adds:
        --module/-m: Python module to import for resource discovery (repeatable)
        --scope/-s: Package scope to filter resources
        --verbose/-v: Enable verbose output

    Args:
        parser: ArgumentParser or subparser to add arguments to
    """
    parser.add_argument(
        "--module",
        "-m",
        dest="modules",
        action="append",
        help="Python module to import for resource discovery (can be repeated)",
    )
    parser.add_argument(
        "--scope",
        "-s",
        help="Package scope to filter resources",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Verbose output",
    )


def create_list_command(
    registry: ResourceRegistry,
    get_resource_type: Callable[[type], str],
) -> Callable[[argparse.Namespace], None]:
    """
    Create a 'list' command handler.

    The returned handler lists all registered resources with their
    resource types. It handles module discovery and scope filtering.

    Args:
        registry: The resource registry to list from
        get_resource_type: Function to extract the resource type string
            from a registered class.

    Returns:
        A command handler function that takes argparse.Namespace

    Example:
        >>> registry = ResourceRegistry()
        >>> list_cmd = create_list_command(registry, lambda cls: cls.__name__)
        >>> # Use with argparse subparser:
        >>> # parser.set_defaults(func=list_cmd)
    """

    def list_command(args: argparse.Namespace) -> None:
        # Import modules to discover resources
        if args.modules:
            for module_path in args.modules:
                discover_resources(
                    module_path, registry, getattr(args, "verbose", False)
                )

        resources = list(registry.get_all(getattr(args, "scope", None)))
        if not resources:
            print("No resources registered.", file=sys.stderr)
            return

        print(f"Registered resources ({len(resources)}):\n")
        for resource_cls in sorted(resources, key=lambda r: r.__name__):
            resource_type = get_resource_type(resource_cls)
            print(f"  {resource_cls.__name__}: {resource_type}")

    return list_command


def create_validate_command(
    registry: ResourceRegistry,
) -> Callable[[argparse.Namespace], None]:
    """
    Create a 'validate' command handler.

    The returned handler validates that all resource references point
    to resources that exist in the registry. Uses dataclass-dsl for
    dependency introspection.

    Args:
        registry: The resource registry to validate

    Returns:
        A command handler function that takes argparse.Namespace

    Raises:
        SystemExit: If validation fails (missing references)

    Example:
        >>> registry = ResourceRegistry()
        >>> validate_cmd = create_validate_command(registry)
        >>> # Use with argparse subparser:
        >>> # parser.set_defaults(func=validate_cmd)
    """

    def validate_command(args: argparse.Namespace) -> None:
        from dataclass_dsl._ordering import get_all_dependencies

        # Import modules to discover resources
        if args.modules:
            for module_path in args.modules:
                discover_resources(
                    module_path, registry, getattr(args, "verbose", False)
                )

        resources = list(registry.get_all(getattr(args, "scope", None)))
        if not resources:
            print("Error: No resources registered.", file=sys.stderr)
            sys.exit(1)

        errors: list[str] = []
        warnings: list[str] = []
        resource_names = {r.__name__ for r in resources}

        for resource_cls in resources:
            try:
                deps = get_all_dependencies(resource_cls)
                for dep in deps:
                    if dep.__name__ not in resource_names:
                        errors.append(
                            f"{resource_cls.__name__} references {dep.__name__} "
                            "which is not registered"
                        )
            except Exception as e:
                warnings.append(
                    f"{resource_cls.__name__}: Could not compute dependencies: {e}"
                )

        # Report results
        verbose = getattr(args, "verbose", False)
        if errors:
            print("Validation FAILED:", file=sys.stderr)
            for error in errors:
                print(f"  ERROR: {error}", file=sys.stderr)
            if warnings and verbose:
                for warning in warnings:
                    print(f"  WARNING: {warning}", file=sys.stderr)
            sys.exit(1)
        elif warnings and verbose:
            print("Validation passed with warnings:", file=sys.stderr)
            for warning in warnings:
                print(f"  WARNING: {warning}", file=sys.stderr)
        else:
            print(f"Validation passed: {len(resources)} resources OK")

    return validate_command


@dataclass
class LintIssue:
    """A linting issue found in source code.

    Attributes:
        line: Line number (1-indexed)
        column: Column number (0-indexed)
        rule_id: Rule identifier (e.g., "WAW001")
        message: Human-readable description
    """

    line: int
    column: int
    rule_id: str
    message: str


class LinterProtocol(Protocol):
    """Protocol for linter functions."""

    def __call__(self, filepath: str) -> list[LintIssue]: ...


class FixerProtocol(Protocol):
    """Protocol for fixer functions."""

    def __call__(self, filepath: str, write: bool = True) -> str: ...


def create_build_command(
    template_class: type[Template],
    registry: ResourceRegistry,
    ref_transformer: Callable[[str, Any, Any], Any] | None = None,
    provider_factory: Callable[[], Any] | None = None,
) -> Callable[[argparse.Namespace], None]:
    """
    Create a 'build' command handler for template generation.

    The returned handler discovers resources from modules, generates
    a template, and outputs JSON or YAML.

    Args:
        template_class: Template class with from_registry() method
        registry: The resource registry to build from
        ref_transformer: Optional callback for transforming refs
        provider_factory: Optional factory for creating a serialization provider

    Returns:
        A command handler function that takes argparse.Namespace

    Example:
        >>> from mypackage import MyTemplate, my_registry, my_transformer
        >>> build_cmd = create_build_command(
        ...     MyTemplate,
        ...     my_registry,
        ...     ref_transformer=my_transformer,
        ... )
        >>> # Use with argparse subparser:
        >>> # build_parser.set_defaults(func=build_cmd)
    """

    def build_command(args: argparse.Namespace) -> None:
        # Import modules to discover resources
        if getattr(args, "modules", None):
            for module_path in args.modules:
                discover_resources(
                    module_path, registry, getattr(args, "verbose", False)
                )

        # Check if any resources are registered
        scope = getattr(args, "scope", None)
        resources = list(registry.get_all(scope))
        if not resources:
            if scope:
                print(f"Error: No resources found in scope '{scope}'", file=sys.stderr)
            else:
                print("Error: No resources registered.", file=sys.stderr)
                print(
                    "Hint: Import your resource modules with --module, e.g.:",
                    file=sys.stderr,
                )
                print("  <command> build --module myapp.infra", file=sys.stderr)
            sys.exit(1)

        # Generate template
        from_registry_kwargs: dict[str, Any] = {
            "scope_package": scope,
            "description": getattr(args, "description", "") or "",
        }
        if ref_transformer is not None:
            from_registry_kwargs["ref_transformer"] = ref_transformer

        template = template_class.from_registry(registry, **from_registry_kwargs)

        # Get provider if factory provided
        provider = provider_factory() if provider_factory else None

        # Output in requested format
        output_format = getattr(args, "format", "json")
        if output_format == "yaml":
            try:
                output = template.to_yaml(provider=provider)
            except ImportError:
                print(
                    "Error: PyYAML required for YAML output. "
                    "Install with: pip install pyyaml",
                    file=sys.stderr,
                )
                sys.exit(1)
        else:
            indent = getattr(args, "indent", 2)
            output = template.to_json(provider=provider, indent=indent)

        print(output)

        if getattr(args, "verbose", False):
            print(
                f"\nGenerated template with {len(template)} resources",
                file=sys.stderr,
            )

    return build_command


def create_lint_command(
    lint_file: LinterProtocol,
    fix_file: FixerProtocol,
    stub_config: Any | None = None,
) -> Callable[[argparse.Namespace], None]:
    """
    Create a 'lint' command handler for code linting.

    The returned handler lints Python files, optionally fixes issues,
    and regenerates stubs after fixes.

    Args:
        lint_file: Function that lints a file and returns issues
        fix_file: Function that fixes a file (called with write=True)
        stub_config: Optional StubConfig for regenerating stubs after fixes

    Returns:
        A command handler function that takes argparse.Namespace

    Example:
        >>> from mypackage.linter import lint_file, fix_file
        >>> from mypackage.stubs import MY_STUB_CONFIG
        >>> lint_cmd = create_lint_command(lint_file, fix_file, MY_STUB_CONFIG)
        >>> # Use with argparse subparser:
        >>> # lint_parser.set_defaults(func=lint_cmd)
    """

    def lint_command(args: argparse.Namespace) -> None:
        path = Path(args.path)
        if not path.exists():
            print(f"Error: Path not found: {path}", file=sys.stderr)
            sys.exit(1)

        # Collect Python files
        if path.is_file():
            files = [path]
        else:
            files = list(path.rglob("*.py"))

        if not files:
            print(f"No Python files found in {path}", file=sys.stderr)
            sys.exit(0)

        total_issues = 0
        files_with_issues = 0
        verbose = getattr(args, "verbose", False)
        do_fix = getattr(args, "fix", False)

        for filepath in files:
            try:
                if do_fix:
                    # Read original to check if we made changes
                    original = filepath.read_text()
                    fixed = fix_file(str(filepath), write=True)
                    if fixed != original:
                        print(f"Fixed: {filepath}")
                        files_with_issues += 1
                else:
                    issues = lint_file(str(filepath))
                    if issues:
                        files_with_issues += 1
                        for issue in issues:
                            loc = f"{filepath}:{issue.line}:{issue.column}"
                            print(f"{loc}: {issue.rule_id} {issue.message}")
                            total_issues += 1
            except Exception as e:
                if verbose:
                    print(f"Error processing {filepath}: {e}", file=sys.stderr)

        # Regenerate stubs after fixing
        if do_fix and files_with_issues > 0 and stub_config is not None:
            from dataclass_dsl._stubs import regenerate_stubs_for_path

            stub_count = regenerate_stubs_for_path(path, stub_config, verbose=verbose)
            if verbose and stub_count > 0:
                print(f"Regenerated stubs for {stub_count} packages")

        if not do_fix:
            if total_issues:
                msg = f"\nFound {total_issues} issues in {files_with_issues} files"
                print(msg, file=sys.stderr)
                sys.exit(1)
            else:
                if verbose:
                    print(f"No issues found in {len(files)} files", file=sys.stderr)
                sys.exit(0)

    return lint_command
