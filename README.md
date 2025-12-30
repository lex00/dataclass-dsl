# dataclass-dsl

Dataclass runtime machinery for declarative DSLs using the **no-parens pattern**.

## The No-Parens Pattern

The no-parens pattern enables declarative references without function calls:

```python
# Traditional approach (requires parentheses)
parent = get_ref(Parent)
parent_id = get_attr(Parent, "Id")

# No-parens pattern (cleaner, more declarative)
parent = Parent          # Direct class reference
parent_id = Parent.Id    # Attribute reference
```

This library provides the runtime machinery to enable this pattern in dataclass-based DSLs.

## Type Annotations with Annotated

For type-safe references, use `typing.Annotated` with the provided markers:

```python
from typing import Annotated
from dataclass_dsl import Ref, Attr, create_decorator

refs = create_decorator()

@refs
class Network:
    cidr: str = "10.0.0.0/16"

@refs
class Subnet:
    # Type checker sees Network, frameworks see Ref() marker
    network: Annotated[Network, Ref()] = None
    # Type checker sees str, frameworks see Attr(Gateway, "Id")
    gateway_id: Annotated[str, Attr(Gateway, "Id")] = ""
```

## Installation

```bash
pip install dataclass-dsl
```

## Quick Start

### Basic Usage

```python
from dataclass_dsl import create_decorator, ResourceRegistry

# Create a domain-specific decorator
registry = ResourceRegistry()
refs = create_decorator(registry=registry)

@refs
class Object1:
    name = "object-1"  # Type inferred as str

@refs
class Object2:
    # No-parens pattern - types inferred from defaults
    parent = Object1
    parent_id = Object1.Id
```

### Multi-File Package with `from . import *`

The primary use case is organizing resources across multiple files:

**`mypackage/objects/__init__.py`**
```python
from dataclass_dsl import setup_resources, StubConfig

stub_config = StubConfig(
    package_name="mypackage",
    core_imports=["refs", "Object1", "Object2"],
)
setup_resources(__file__, __name__, globals(), stub_config=stub_config)
```

**`mypackage/objects/object1.py`**
```python
from . import *  # refs available via setup_resources()

@refs
class Object1:
    name = "object-1"
```

**`mypackage/objects/object2.py`**
```python
from . import *  # refs, Object1 available via setup_resources()

@refs
class Object2:
    # No-parens pattern - reference Object1 without imports
    parent = Object1
    parent_id = Object1.Id
```

**Usage:**
```python
from mypackage.objects import *  # All objects available

obj = Object2()
print(obj.parent)     # <class 'Object1'>
print(obj.parent_id)  # AttrRef(Object1, 'Id')
```

## Core Features

### No-Parens Class References

Reference another decorated class directly by name:

```python
@refs
class Object1:
    value = "base"

@refs
class Object2:
    # No-parens: Object1 becomes a field default
    parent = Object1

obj = Object2()
assert obj.parent is Object1
```

### No-Parens Attribute References (AttrRef)

Access attributes on decorated classes to create `AttrRef` markers:

```python
@refs
class Object1:
    name = "object-1"

@refs
class Object2:
    # No-parens: Object1.Id returns AttrRef(Object1, "Id")
    parent_id = Object1.Id

obj = Object2()
assert obj.parent_id.target is Object1
assert obj.parent_id.attr == "Id"
```

### Dependency Detection

The library detects dependencies from both patterns:

```python
from dataclass_dsl import get_all_dependencies

deps = get_all_dependencies(Object2)
assert Object1 in deps
```

### Topological Ordering

Sort objects by their dependencies for creation/deletion:

```python
from dataclass_dsl import get_creation_order, get_deletion_order

@refs
class Object1:
    name = "base"

@refs
class Object2:
    parent = Object1

@refs
class Object3:
    parent = Object2

# Dependencies first (for creation)
order = get_creation_order([Object3, Object2, Object1])
# -> [Object1, Object2, Object3]

# Dependents first (for deletion)
order = get_deletion_order([Object3, Object2, Object1])
# -> [Object3, Object2, Object1]
```

### Resource Registry

Track decorated classes for discovery:

```python
registry = ResourceRegistry()
refs = create_decorator(registry=registry)

@refs
class Object1:
    name = "base"

@refs
class Object2:
    parent = Object1

@refs
class Object3:
    parent = Object2

all_objects = registry.get_all()
assert Object1 in all_objects
assert Object2 in all_objects
assert Object3 in all_objects
```

### Template Aggregation

Collect and serialize objects:

```python
from dataclass_dsl import Template

template = Template.from_registry(
    registry=registry,
    description="My objects",
)

# Objects returned in dependency order
for obj in template.get_dependency_order():
    print(type(obj).__name__)
```

### Provider Pattern

Abstract interface for domain-specific serialization:

```python
from dataclass_dsl import Provider

class MyProvider(Provider):
    name = "myformat"

    def serialize_ref(self, source, target):
        return {"ref": target.__name__}

    def serialize_attr(self, source, target, attr_name):
        return {"attr": f"{target.__name__}.{attr_name}"}

    def serialize_resource(self, resource):
        return {"type": type(resource).__name__}

output = template.to_dict(provider=MyProvider())
```

### IDE Stub Generation

Generate `.pyi` files for IDE autocomplete with dynamic imports:

```python
from dataclass_dsl import StubConfig, generate_stub_file

config = StubConfig(
    package_name="mypackage",
    core_imports=["refs", "Object1", "Object2"],
)
generate_stub_file(package_path, config=config)
```

## API Reference

### Core

- `AttrRef` - Runtime marker for attribute references (`Object1.Id`)
- `RefMeta` - Metaclass enabling no-parens attribute interception
- `create_decorator()` - Factory for domain-specific decorators

### Registry

- `ResourceRegistry` - Thread-safe registry for decorated classes

### Ordering

- `get_all_dependencies()` - Get all dependencies of a class
- `topological_sort()` - Sort by dependency order
- `get_creation_order()` - Dependencies first
- `get_deletion_order()` - Dependents first
- `detect_cycles()` - Find circular dependencies
- `get_dependency_graph()` - Build adjacency list

### Provider

- `Provider` - Abstract base class for serialization

### Template

- `Template` - Base class for object aggregation

### Loader

- `setup_resources()` - Import modules in dependency order for `from . import *`

### Stubs

- `StubConfig` - Configuration for stub generation
- `generate_stub_file()` - Generate `.pyi` for IDE support
- `regenerate_stubs_for_path()` - Regenerate stubs after code changes

### Helpers

- `is_attr_ref()` - Check if object is AttrRef
- `is_class_ref()` - Check if object is decorated class
- `get_ref_target()` - Extract target from reference
- `apply_metaclass()` - Apply metaclass to existing class

### Type Markers (Annotated-based)

- `Ref` - Marker for reference relationship (`Annotated[T, Ref()]`)
- `Attr` - Marker for attribute reference (`Annotated[str, Attr(T, "name")]`)
- `RefList` - Marker for list of references
- `RefDict` - Marker for dict with reference values
- `ContextRef` - Marker for context reference
- `RefInfo` - Metadata about a reference field
- `get_refs()` - Extract reference info from type hints
- `get_dependencies()` - Get dependency classes from type hints

### Base Classes (for domain packages)

- `Resource` - Abstract base class for infrastructure resources
- `PropertyType` - Abstract base class for nested property types

### CLI Framework

- `discover_resources()` - Import module to trigger resource registration
- `add_common_args()` - Add standard --module, --scope, --verbose args
- `create_list_command()` - Factory for 'list' command handler
- `create_validate_command()` - Factory for 'validate' command handler
- `create_build_command()` - Factory for 'build' command handler
- `create_lint_command()` - Factory for 'lint' command handler with auto-fix
- `LintIssue` - Dataclass for structured lint results
- `RefTransformer` - Type alias for ref transformation callbacks

### Inspection Utilities

- `get_package_modules()` - Find all submodule names in a package
- `get_module_constants()` - Extract UPPERCASE constants from a module
- `get_module_exports()` - Get public exports from a module
- `collect_exports()` - Collect exports from multiple modules
- `build_reverse_constant_map()` - Build value→name mapping from constants

### IR (Intermediate Representation)

- `IRProperty` - A property key-value pair
- `IRParameter` - A template parameter
- `IRResource` - A parsed resource with properties
- `IROutput` - A template output
- `IRTemplate` - Complete parsed template

### Serialization Framework

- `FieldMapper` - Abstract base for field name mapping
- `PascalCaseMapper` - Maps snake_case to/from PascalCase
- `SnakeCaseMapper` - Identity mapper for snake_case formats
- `ValueSerializer` - Abstract base for value serialization

### Codegen Utilities

- `PYTHON_KEYWORDS` - Set of Python reserved keywords
- `to_snake_case()` - Convert PascalCase to snake_case
- `to_pascal_case()` - Convert snake_case to PascalCase
- `sanitize_python_name()` - Escape Python keywords
- `sanitize_class_name()` - Ensure valid class names
- `is_valid_python_identifier()` - Check identifier validity
- `escape_string()` - Escape for Python source code
- `escape_docstring()` - Escape for docstrings

### Importer Framework (for template parsing)

Generic graph algorithms for dependency ordering in template importers:

- `find_sccs_in_graph()` - Find strongly connected components (Tarjan's algorithm)
- `topological_sort_graph()` - Sort nodes in dependency order
- `order_scc_by_dependencies()` - Order nodes within an SCC to minimize forward refs

## Design Rationale

### Why Two Patterns?

dataclass-dsl provides two complementary mechanisms for expressing references:

1. **No-parens pattern** (`parent = Parent`) - Runtime detection
2. **Annotated markers** (`parent: Annotated[Parent, Ref()]`) - Static type checking

These serve different purposes:

| Concern | No-Parens | Annotated |
|---------|-----------|-----------|
| Serialization | ✓ Detected from class defaults | ✓ Detected from type hints |
| Dependency ordering | ✓ `is_class_ref(default)` | ✓ `get_dependencies(cls)` |
| IDE autocomplete | ✗ Sees `type[Parent]` | ✓ Sees `Parent` directly |
| Type error detection | ✗ No static checking | ✓ Wrong type = red squiggle |
| Refactoring support | ✗ String-like | ✓ Rename propagates |

### When No-Parens Is Sufficient

For declarative class definitions with class-level defaults, no-parens handles everything at runtime:

```python
@refs
class MyFunction:
    role = MyRole          # Detected as dependency
    role_arn = MyRole.Arn  # Detected as attribute reference
```

The runtime can detect `MyRole` is a dependency because it *is* the value.

### When Annotated Markers Add Value

**1. IDE Type Checking** - Critical for catching errors before runtime:

```python
@refs
class MyFunction:
    # IDE shows error if you pass a Bucket where Role expected
    role: Annotated[MyRole, Ref()] = MyRole
```

**2. Imperative Style** - When constructing instances programmatically:

```python
# Without annotation, IDE can't validate this
function = MyFunction(role=some_role)

# With annotation on the class, IDE catches type mismatches
role: Annotated[MyRole, Ref()]
```

**3. Forward References** - When the target class isn't defined yet:

```python
from __future__ import annotations

@refs
class MyFunction:
    # Can reference MyRole before it's defined
    role: Annotated[MyRole, Ref()] = None

@refs
class MyRole:
    name = "my-role"
```

### The Bottom Line

- **No-parens** handles runtime behavior (serialization, dependency detection)
- **Annotated markers** handle static analysis (IDE support, type checking)

If IDE type checking is important to your workflow, use both. The runtime detection ensures serialization works regardless of annotations, while annotations give you the IDE experience.

## The No-Parens Pattern in Detail

The no-parens pattern works through two mechanisms:

1. **RefMeta Metaclass**: Intercepts attribute access on decorated classes. When you access an undefined attribute like `Object1.Id`, it returns `AttrRef(Object1, "Id")` instead of raising `AttributeError`.

2. **Decorator Processing**: The `create_decorator()` factory creates decorators that:
   - Apply `@dataclass` transformation
   - Apply `RefMeta` metaclass
   - Handle class and AttrRef defaults as dataclass fields
   - Register classes with the optional registry

This enables clean, declarative DSLs where relationships between objects are expressed directly through class names rather than function calls.

## License

Apache 2.0
