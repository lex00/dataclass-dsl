# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2026-01-06

### Added

- Export `DecoratorType` Protocol for type-safe decorator parameter passing (#9)
- Add `resource_predicate` parameter to `setup_resources()` for inheritance-based resource detection (#8)

### Fixed

- Preserve class identity when RefMeta is already applied, fixing AttrRef target identity issues (#10)

## [1.0.1] - 2026-01-04

### Changed

- Replace mypy and pyright with ty (Astral's type checker) for type checking
- Simplify CI workflow from dual type checker matrix to single ty run
- Update documentation to use uv syntax for installation commands

## [1.0.0] - 2026-01-03

### Changed

- Bump version to 1.0.0 (Production/Stable)
- Change license from Apache 2.0 to MIT
- Update specification to version 1.0

## [0.1.4] - 2025-12-31

### Changed

- Restructure documentation for end-user focus
  - README now leads with clean DSL syntax (no decorators visible)
  - Move technical internals to new `docs/INTERNALS.md`
  - Update `docs/guides/concepts.md` to remove decorator examples
  - Separate documentation by audience: end users vs domain package authors

### Removed

- Remove `examples/dsl-simple` synthetic example

### Added

- Add `examples/aws_s3_log_bucket` real-world example from [wetwire-aws](https://github.com/lex00/wetwire/tree/main/python/packages/wetwire-aws)
  - Demonstrates cross-file references (storage.py → bucket.py)
  - Includes full CloudFormation output in README
  - Installable as a Python package with `wetwire-aws` dependency

## [0.1.3] - 2025-12-29

### Fixed

- Sync `__version__` with pyproject.toml version
- Add `regenerate_stubs_for_path` to public exports (`__all__`)

### Changed

- Clarify planned vs implemented features in documentation
- Mark `@computed`, `when()`, `match()` as planned features in concepts guide
- Update SPECIFICATION.md to identify extension points (Presets, Traits, Computed Values, Conditionals)
- Update conformance table to reflect what's implemented in core vs domain packages

## [0.1.2] - 2024-12-29

### Changed

- Replace black with ruff format for code formatting
- Move pytest to regular dependencies in dsl-simple example

## [0.1.0] - 2024-12-27

### Added

- Initial release
- `AttrRef` - Runtime marker for attribute references (no-parens pattern)
- `RefMeta` - Metaclass enabling no-parens attribute interception
- `create_decorator()` - Factory for creating domain-specific decorators
- `ResourceRegistry` - Thread-safe registry for decorated classes
- Dependency ordering utilities:
  - `get_all_dependencies()` - Get all dependencies of a class
  - `topological_sort()` - Sort classes by dependency order
  - `get_creation_order()` - Get creation order (dependencies first)
  - `get_deletion_order()` - Get deletion order (dependents first)
  - `detect_cycles()` - Detect circular dependencies
  - `get_dependency_graph()` - Build dependency graph
- `Provider` - Abstract base class for serialization
- `Template` - Base class for resource aggregation
- `setup_resources()` - Import modules in dependency order for `from . import *`
- Stub generation for IDE support:
  - `StubConfig` - Configuration for stub generation
  - `generate_stub_file()` - Generate `.pyi` files
- Helper utilities:
  - `is_attr_ref()` - Check if object is AttrRef
  - `is_class_ref()` - Check if object is decorated class
  - `get_ref_target()` - Extract target from reference
  - `apply_metaclass()` - Apply metaclass to existing class
- Annotated-based type markers (no external dependencies):
  - `Ref` - Marker for reference relationship
  - `Attr` - Marker for attribute reference
  - `RefList` - Marker for list of references
  - `RefDict` - Marker for dict with reference values
  - `ContextRef` - Marker for context reference
  - `RefInfo` - Metadata about a reference field
  - `get_refs()` - Extract reference info from type hints
  - `get_dependencies()` - Get dependency classes from type hints
