# IDE Support & Type Checking

The dataclass-dsl pattern provides full IDE support through:
- Type annotations on all classes and functions
- Generated `.pyi` stub files for dynamic imports
- Compatibility with Pylance, ty, and other type checkers

## The Challenge

Packages using dataclass-dsl often use centralized imports for clean, concise code:

```python
from . import *  # noqa: F403, F401

class MyResource(SomeType):
    other = OtherResource  # Available without explicit import
```

This works at runtime because the package's `__init__.py` dynamically exports all necessary symbols. However, IDEs like VSCode/Pylance can't see these dynamic exports without help.

## The Solution: .pyi Stub Files

Type stub files (`.pyi`) declare what a module exports. When placed alongside `__init__.py`, they tell the IDE:

- What names are available via star imports
- Type information for all exported classes
- Re-exports from dataclass-dsl packages

```
myproject/
├── __init__.py      # Your code with dynamic exports
├── __init__.pyi     # Generated stub (declares exports)
├── resources.py
└── policies.py
```

### Example Stub File

```python
# __init__.pyi (generated)
from dataclass_dsl import Ref as Ref
from dataclass_dsl import Attr as Attr

# For domain-specific projects:
from my_domain import my_decorator as my_decorator
from my_domain import ref as ref
from my_domain import get_att as get_att

from .resources import MyBucket as MyBucket
from .resources import MyFunction as MyFunction
from .policies import MyPolicy as MyPolicy
```

This enables:
- IDE autocomplete for `MyBucket`, `MyFunction`, etc.
- Type checking for reference annotations
- Error detection for undefined references

## Generating Stub Files

### Using StubConfig

dataclass-dsl provides `StubConfig` and `generate_stub_file()` for stub generation:

```python
from dataclass_dsl import StubConfig, generate_stub_file

config = StubConfig(
    package_name="mypackage",
    core_imports=["my_decorator", "Ref", "Attr"],
)
generate_stub_file(package_path, config=config)
```

### Manual Stub Files

Stub files can also be created manually. A typical stub file exports all symbols that should be available:

```python
# my_project/__init__.pyi
# Re-export all resource classes
from .storage import DataBucket as DataBucket
from .compute import ProcessorFunction as ProcessorFunction

# Re-export dataclass-dsl types
from dataclass_dsl import Ref as Ref, Attr as Attr
from my_domain import my_decorator as my_decorator
```

### When to Regenerate

Regenerate stubs after:
- Creating new resource classes
- Adding new parameters or outputs
- Renaming classes
- Modifying package-level imports

## VSCode/Pylance Setup

Pylance should work automatically once stubs are generated. If you see "unknown" errors:

1. Ensure stubs are generated
2. Reload VSCode window: Cmd/Ctrl+Shift+P → "Reload Window"
3. Check Python interpreter is set to your venv

### Settings

For best results, add to `.vscode/settings.json`:

```json
{
  "python.analysis.typeCheckingMode": "basic",
  "python.analysis.diagnosticSeverityOverrides": {
    "reportUnusedImport": "warning"
  }
}
```

## ty Configuration

This project uses [ty](https://github.com/astral-sh/ty) (Astral's type checker) for type checking. To run type checks:

```bash
uv run ty check src/
```

ty is configured automatically and requires no additional setup.

## Handling Star Import Warnings

Add `# noqa` comments to suppress flake8/ruff warnings:

```python
from . import *  # noqa: F403, F401
```

These warnings are expected for the dataclass-dsl pattern. The stub files ensure type safety despite the dynamic imports.

## Troubleshooting

### "Cannot find module" errors

- Ensure stub files exist (`.pyi` alongside `__init__.py`)
- Regenerate stub files if they're missing
- Check you're in the correct virtual environment

### Stubs out of date

- Regenerate stubs after adding/renaming classes
- Keep stubs in sync during active development

### IDE shows "partially unknown" types

- Regenerate stubs and reload IDE
- Check that generated `.pyi` files include your new classes
- Verify the package's `__init__.py` properly exports all symbols

### Star import not recognized

Some type checkers struggle with `from . import *`. If issues persist:

1. Ensure stub file lists all exports explicitly
2. Use `as` aliases: `from .resources import MyBucket as MyBucket`
3. Consider explicit imports for critical symbols

## Best Practices

1. **Commit stub files**: Include `.pyi` files in version control for team consistency
2. **CI validation**: Run type checking in CI to catch issues early
3. **Keep stubs updated**: Regenerate when adding or renaming resources
4. **Explicit re-exports**: Use `as` aliasing in stubs for clarity

## See Also

- [Concepts](concepts.md) - Core dataclass-dsl concepts
- [CLI Framework](cli_framework.md) - CLI utilities
