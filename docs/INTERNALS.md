# Internals Guide

This guide is for developers building domain packages on top of dataclass-dsl. If you're using a domain package, you don't need to read this — just follow that package's documentation.

## Overview

To build a domain package, you'll create:

1. **A decorator** — Transforms user classes into dataclasses with reference detection
2. **A loader** — Sets up multi-file packages with `from . import *` support
3. **A provider** — Serializes resources to your target format (JSON, YAML, etc.)
4. **A template** — Aggregates resources from the registry for output

The goal: your users write clean declarative classes, and all the machinery is invisible.

---

## The No-Parens Pattern

dataclass-dsl enables two complementary patterns for expressing references:

```python
# Traditional approach (requires parentheses)
parent = get_ref(Parent)
parent_id = get_attr(Parent, "Id")

# No-parens pattern (cleaner, more declarative)
parent = Parent          # Direct class reference
parent_id = Parent.Id    # Attribute reference
```

This works through two mechanisms:

1. **RefMeta Metaclass** — Intercepts attribute access on decorated classes
2. **Decorator Processing** — Detects class and AttrRef defaults in field assignments

---

## Core Components

### RefMeta Metaclass

When you access an undefined attribute on a decorated class, `RefMeta` returns an `AttrRef` marker instead of raising `AttributeError`:

```python
from dataclass_dsl import RefMeta

class MyClass(metaclass=RefMeta):
    name = "example"

# Accessing undefined attribute returns AttrRef
ref = MyClass.Id  # AttrRef(MyClass, "Id")
ref.target        # MyClass
ref.attr          # "Id"
```

Chained access is supported:

```python
ref = MyClass.Endpoint.Address  # AttrRef(MyClass, "Endpoint.Address")
```

### AttrRef Marker

`AttrRef` is the runtime marker for attribute references:

```python
from dataclass_dsl import AttrRef

ref = AttrRef(MyClass, "Arn")
ref.target  # The class being referenced
ref.attr    # The attribute name

# Supports equality and hashing
ref == AttrRef(MyClass, "Arn")  # True
{ref}  # Can be used in sets
```

### create_decorator()

The decorator factory creates domain-specific decorators:

```python
from dataclass_dsl import create_decorator, ResourceRegistry

registry = ResourceRegistry()
refs = create_decorator(registry=registry)

@refs
class Object1:
    name = "object-1"  # Type inferred as str
    tags = []          # Converted to field(default_factory=list)

@refs
class Object2:
    parent = Object1       # Detected as class reference
    parent_id = Object1.Id # Detected as AttrRef
```

The decorator:
- Applies `@dataclass` transformation
- Infers field types from default values
- Converts mutable defaults (lists, dicts) to `field(default_factory=...)`
- Applies `RefMeta` metaclass
- Registers the class with the optional registry

### ResourceRegistry

Thread-safe registry for tracking decorated classes:

```python
from dataclass_dsl import ResourceRegistry, create_decorator

registry = ResourceRegistry()
refs = create_decorator(registry=registry)

@refs
class Object1:
    name = "base"

@refs
class Object2:
    parent = Object1

# Query the registry
"Object1" in registry           # True
Object1 in registry.get_all()   # True

# Filter by package
registry.get_all(scope_package="myproject.resources")

# Get by name
registry.get_by_name("Object1")  # <class 'Object1'>
```

---

## Multi-File Packages

### setup_resources()

Enables `from . import *` across multiple files by loading them in dependency order:

**`mypackage/resources/__init__.py`**
```python
from dataclass_dsl import setup_resources, StubConfig
from mypackage import my_decorator

stub_config = StubConfig(
    package_name="mypackage",
    core_imports=["my_decorator"],
)

setup_resources(
    __file__,
    __name__,
    globals(),
    stub_config=stub_config,
    extra_namespace={"my_decorator": my_decorator},
)
```

**`mypackage/resources/vpc.py`**
```python
from . import *

@my_decorator
class AppVPC:
    resource: VPC
    cidr_block = "10.0.0.0/16"
```

**`mypackage/resources/subnet.py`**
```python
from . import *

@my_decorator
class AppSubnet:
    resource: Subnet
    vpc = AppVPC  # Available because vpc.py loaded first
    cidr_block = "10.0.1.0/24"
```

How it works:
1. Discovers all Python files in the package directory
2. Parses to find class definitions and dependencies
3. Builds a dependency graph
4. Topologically sorts modules (dependencies first)
5. Loads each module, injecting already-loaded classes
6. Generates `.pyi` stub files for IDE support

### StubConfig

Configuration for IDE stub generation:

```python
from dataclass_dsl import StubConfig

stub_config = StubConfig(
    package_name="mypackage",
    core_imports=["my_decorator", "BaseResource"],
)
```

The generated `__init__.pyi` file provides full IDE support (autocomplete, go-to-definition, type checking) for dynamically imported classes.

### Manual Stub Generation

```python
from dataclass_dsl import generate_stub_file, regenerate_stubs_for_path

# Generate stub for a package
generate_stub_file(package_path, config=stub_config)

# Regenerate after code changes
regenerate_stubs_for_path(package_path)
```

### Auto-Decoration

To achieve the "invisible decorator" pattern where users don't write `@decorator` on their classes, use the `auto_decorate` option:

```python
from dataclass_dsl import setup_resources, create_decorator

my_decorator = create_decorator()

setup_resources(
    __file__,
    __name__,
    globals(),
    auto_decorate=True,
    decorator=my_decorator,
)
```

This automatically decorates any class with a `resource:` annotation:

```python
# User writes this (no decorator):
class LogBucket:
    resource: s3.Bucket
    bucket_encryption = LogBucketEncryption

# Becomes equivalent to:
@my_decorator
class LogBucket:
    resource: s3.Bucket
    bucket_encryption = LogBucketEncryption
```

**Options:**

| Parameter | Default | Description |
|-----------|---------|-------------|
| `auto_decorate` | `False` | Enable auto-decoration |
| `decorator` | Required | The decorator function to apply |
| `resource_field` | `"resource"` | Annotation field that identifies resource classes |
| `marker_attr` | `"_refs_marker"` | Attribute used to detect already-decorated classes |

**How it works:**

1. After all modules are loaded, `setup_resources()` scans `package_globals`
2. For each class with a `resource:` annotation that isn't already decorated, it applies the decorator
3. AttrRef targets are updated to point to the new decorated classes (since decoration creates new class objects)

---

## Dependency Ordering

### get_all_dependencies()

Detects dependencies from both runtime values and type hints:

```python
from dataclass_dsl import get_all_dependencies

@refs
class Object1:
    name = "base"

@refs
class Object2:
    parent = Object1
    parent_id = Object1.Id

deps = get_all_dependencies(Object2)
# {Object1}
```

### Topological Sorting

Sort resources by dependency order:

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
# [Object1, Object2, Object3]

# Dependents first (for deletion)
order = get_deletion_order([Object3, Object2, Object1])
# [Object3, Object2, Object1]
```

### Cycle Detection

Detect circular dependencies:

```python
from dataclass_dsl import detect_cycles, get_dependency_graph

cycles = detect_cycles([Object1, Object2, Object3])
# Returns list of cycles, empty if none

graph = get_dependency_graph([Object1, Object2, Object3])
# Returns adjacency list: {Object2: {Object1}, Object3: {Object2}, ...}
```

---

## Serialization

### Provider Pattern

Abstract interface for format-specific serialization:

```python
from dataclass_dsl import Provider

class MyProvider(Provider):
    name = "myformat"

    def serialize_ref(self, source, target):
        """Serialize a class reference."""
        return {"$ref": target.__name__}

    def serialize_attr(self, source, target, attr_name):
        """Serialize an attribute reference."""
        return {"$getattr": f"{target.__name__}.{attr_name}"}

    def serialize_resource(self, resource):
        """Serialize a resource instance."""
        return {
            "type": type(resource).__name__,
            "properties": {...}
        }
```

### Template

Aggregates resources from the registry:

```python
from dataclass_dsl import Template

template = Template.from_registry(
    registry=registry,
    description="My Stack",
    scope_package="myproject.resources",
)

# Resources in dependency order
for resource in template.get_dependency_order():
    print(type(resource).__name__)

# Serialize
output = template.to_dict(provider=MyProvider())
json_output = template.to_json(provider=MyProvider())
yaml_output = template.to_yaml(provider=MyProvider())
```

---

## Type Markers (Annotated-based)

For static type checking alongside runtime detection, use `typing.Annotated`:

```python
from typing import Annotated
from dataclass_dsl import Ref, Attr, RefList

@refs
class Subnet:
    # Type checker sees Network, runtime sees Ref() marker
    network: Annotated[Network, Ref()] = None

    # Type checker sees str, runtime sees Attr(Gateway, "Id")
    gateway_id: Annotated[str, Attr(Gateway, "Id")] = ""

    # Type checker sees list[SecurityGroup]
    security_groups: Annotated[list[SecurityGroup], RefList()] = None
```

### Available Markers

| Marker | Purpose |
|--------|---------|
| `Ref()` | Reference to another resource |
| `Attr(target, name)` | Reference to a specific attribute |
| `RefList()` | List of references |
| `RefDict()` | Dict with reference values |
| `ContextRef(name)` | Reference to a context value |

### Introspection

```python
from dataclass_dsl import get_refs, get_dependencies

# Extract RefInfo from type hints
refs = get_refs(Subnet)

# Get dependency classes
deps = get_dependencies(Subnet, transitive=False)
```

---

## Hiding the Decorator

To achieve the "zero decorators" experience for end users, use the built-in `auto_decorate` option:

```python
from dataclass_dsl import setup_resources, create_decorator

my_decorator = create_decorator()

setup_resources(
    __file__,
    __name__,
    globals(),
    auto_decorate=True,
    decorator=my_decorator,
)
```

This automatically decorates any class with a `resource:` annotation. See [Auto-Decoration](#auto-decoration) for details.

The key insight: the `resource:` type annotation marks a class for decoration, but the decorator is applied by the loader, not the user.

---

## Base Classes

For domain packages that need common functionality:

### Resource

Abstract base for infrastructure resources:

```python
from dataclass_dsl import Resource

class CloudFormationResource(Resource):
    resource_type: ClassVar[str] = "AWS::Service::Resource"

    def to_dict(self) -> dict:
        return {"Type": self.resource_type, ...}
```

### PropertyType

For nested property types:

```python
from dataclass_dsl import PropertyType

class EncryptionConfig(PropertyType):
    algorithm: str = "AES256"
    key_id: str = None
```

---

## CLI Utilities

Helpers for building CLI tools:

```python
from dataclass_dsl import (
    discover_resources,
    add_common_args,
    create_list_command,
    create_validate_command,
    create_build_command,
    create_lint_command,
)

# Import module to trigger registration
discover_resources("mypackage.resources")

# Add standard CLI args (--module, --scope, --verbose)
add_common_args(parser)

# Create command handlers
list_cmd = create_list_command(registry)
validate_cmd = create_validate_command(registry, provider)
build_cmd = create_build_command(registry, provider, template_class)
lint_cmd = create_lint_command(registry, lint_rules)
```

---

## Utility Functions

### Helpers

```python
from dataclass_dsl import is_attr_ref, is_class_ref, get_ref_target, apply_metaclass

is_attr_ref(obj)              # Check if object is AttrRef
is_class_ref(obj, marker)     # Check if object is decorated class
get_ref_target(obj)           # Extract target from reference
apply_metaclass(cls, meta)    # Apply metaclass to existing class
```

### Inspection

```python
from dataclass_dsl import (
    get_package_modules,
    get_module_constants,
    get_module_exports,
    collect_exports,
    build_reverse_constant_map,
)
```

### Code Generation

```python
from dataclass_dsl import (
    to_snake_case,
    to_pascal_case,
    sanitize_python_name,
    sanitize_class_name,
    is_valid_python_identifier,
    escape_string,
    escape_docstring,
    PYTHON_KEYWORDS,
)
```

### Graph Algorithms

```python
from dataclass_dsl import (
    find_sccs_in_graph,      # Tarjan's SCC algorithm
    topological_sort_graph,   # DAG-based ordering
    order_scc_by_dependencies,
)
```

---

## Complete Example

See [examples/aws_s3_log_bucket/](../examples/aws_s3_log_bucket/) for an example of what a domain package produces. This example is from [wetwire-aws](https://github.com/lex00/wetwire/tree/main/python/packages/wetwire-aws) and demonstrates:

- Single import (`from . import *`)
- No decorators visible to users
- Flat wrapper classes with `resource:` type annotations
- Type-safe references to AWS resource types
- Composition through class references

---

## API Reference Summary

### Core
- `AttrRef` — Runtime marker for attribute references
- `RefMeta` — Metaclass enabling no-parens attribute interception
- `create_decorator()` — Factory for domain-specific decorators
- `ResourceRegistry` — Thread-safe class registry

### Ordering
- `get_all_dependencies()` — Get dependencies of a class
- `topological_sort()` — Sort by dependency order
- `get_creation_order()` — Dependencies first
- `get_deletion_order()` — Dependents first
- `detect_cycles()` — Find circular dependencies
- `get_dependency_graph()` — Build adjacency list

### Serialization
- `Provider` — Abstract base for format-specific serialization
- `Template` — Resource aggregation and output
- `FieldMapper` / `PascalCaseMapper` / `SnakeCaseMapper` — Field name mapping
- `ValueSerializer` — Value serialization

### Loader
- `setup_resources()` — Multi-file package loader
- `StubConfig` — Stub generation config
- `generate_stub_file()` — Generate `.pyi` files
- `regenerate_stubs_for_path()` — Regenerate stubs

### Type Markers
- `Ref` / `Attr` / `RefList` / `RefDict` / `ContextRef` — Annotated markers
- `RefInfo` — Reference metadata
- `get_refs()` / `get_dependencies()` — Introspection

### Base Classes
- `Resource` — Abstract infrastructure resource
- `PropertyType` — Nested property types

### IR (Intermediate Representation)
- `IRProperty` / `IRParameter` / `IRResource` / `IROutput` / `IRTemplate`
