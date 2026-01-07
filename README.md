# dataclass-dsl

[![CI](https://github.com/lex00/dataclass-dsl/actions/workflows/ci.yml/badge.svg)](https://github.com/lex00/dataclass-dsl/actions/workflows/ci.yml)
[![PyPI Version](https://img.shields.io/pypi/v/dataclass-dsl.svg)](https://pypi.org/project/dataclass-dsl/)
[![Python Version](https://img.shields.io/pypi/pyversions/dataclass-dsl.svg)](https://pypi.org/project/dataclass-dsl/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Build declarative Python DSLs where infrastructure and configuration look like this:

```python
from . import *

class LogBucketEncryption(s3.Bucket.BucketEncryption):
    server_side_encryption_configuration = [LogBucketEncryptionRule]

class LogBucket(s3.Bucket):
    bucket_encryption = LogBucketEncryption
    public_access_block_configuration = LogBucketPublicAccessBlock
    versioning_configuration = LogBucketVersioning
```

No decorators. No function calls. No boilerplate.

## The Pattern

Domain packages built on dataclass-dsl share three properties:

| Property | What it means |
|----------|---------------|
| **Single import** | `from . import *` — everything available, loaded in dependency order |
| **Zero decorators** | Classes are plain declarations, machinery is invisible |
| **Inheritance wrappers** | Each class inherits from a resource type with simple attribute assignments |

The result reads like configuration, but with full Python power: IDE autocomplete, type checking, refactoring, and the ability to use variables, loops, and conditionals when needed.

## What This Enables

**Reference other resources by class name:**
```python
class AppSubnet(Subnet):
    vpc = AppVPC                    # Reference to another resource
    cidr_block = "10.0.1.0/24"
```

**Reference specific attributes:**
```python
class LambdaFunction(Function):
    role_arn = ExecutionRole.Arn    # Gets the Arn of ExecutionRole
```

**Compose nested configurations:**
```python
class BucketEncryption(s3.Bucket.BucketEncryption):
    server_side_encryption_configuration = [EncryptionRule]

class MyBucket(s3.Bucket):
    bucket_encryption = BucketEncryption
```

**Use lists and maps of references:**
```python
class LoadBalancer(ALB):
    subnets = [SubnetA, SubnetB, SubnetC]
    security_groups = [WebSecurityGroup]
```

## How It Works

dataclass-dsl provides the runtime machinery that makes this pattern possible:

- **Automatic dependency detection** — References between classes are detected at runtime
- **Topological ordering** — Resources are serialized in dependency order
- **Multi-file support** — `setup_resources()` loads files in the right order, enabling `from . import *`
- **IDE stub generation** — Full autocomplete and type checking despite dynamic imports

Domain packages use these primitives to create decorators and loaders that are invisible to end users.

## Installation

```bash
uv add dataclass-dsl
```

## Using a Domain Package

If you're using a domain package built on dataclass-dsl (like an AWS CDK alternative or Kubernetes manifest generator), follow that package's documentation. You'll write clean declarative classes without needing to understand the internals.

## Building a Domain Package

If you're creating a domain package, see the [Internals Guide](docs/INTERNALS.md) for:

- Creating a domain-specific decorator with `create_decorator()`
- Setting up multi-file packages with `setup_resources()`
- Implementing a `Provider` for your target format
- Generating IDE stubs for `from . import *`

Also see the [AWS S3 example](examples/aws_s3_log_bucket/) to see what a domain package produces.

## Documentation

- [Core Concepts](docs/guides/concepts.md) — The wrapper pattern, references, and templates
- [Internals Guide](docs/INTERNALS.md) — Building domain packages
- [Specification](docs/spec/SPECIFICATION.md) — Formal specification
- [CLI Framework](docs/guides/cli_framework.md) — CLI utilities for domain packages

## License

MIT
