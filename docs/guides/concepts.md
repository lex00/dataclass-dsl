# Core Concepts

This guide explains the fundamental patterns you'll use when writing declarative code with a dataclass-dsl based domain package.

## Table of Contents

1. [The Wrapper Pattern](#the-wrapper-pattern)
2. [The No-Parens Principle](#the-no-parens-principle)
3. [References](#references)
4. [Multi-File Organization](#multi-file-organization)
5. [Context Values](#context-values)
6. [Output Formats](#output-formats)

---

## The Wrapper Pattern

The core pattern is **wrapping**: you create a class that wraps an underlying resource type.

```python
class LogBucket:
    resource: s3.Bucket        # The type being wrapped
    bucket_name = "app-logs"   # Properties of that type
```

**Why wrapping?**

1. **Naming**: Your class name (`LogBucket`) becomes the logical resource name
2. **Referencing**: Other resources refer to `LogBucket`, not a string ID
3. **Type safety**: The domain package knows what properties are valid for `s3.Bucket`
4. **Flat structure**: All properties are class attributes, no nesting

**The `resource` field is special**: It declares what you're wrapping. It's a type annotation only — never assigned a value.

---

## The No-Parens Principle

References to other resources are expressed as **class names without parentheses**:

```python
class AppSubnet:
    resource: Subnet
    vpc = AppVPC              # Reference — just the class name
    cidr_block = "10.0.1.0/24"
```

Compare to traditional approaches:

```python
# Traditional style (requires explicit id, scope, function calls)
subnet = Subnet(self, "AppSubnet", vpc=app_vpc, cidr_block="10.0.1.0/24")

# dataclass-dsl style (flat, no function calls for references)
class AppSubnet:
    resource: Subnet
    vpc = AppVPC
    cidr_block = "10.0.1.0/24"
```

**Benefits:**

- **Readable**: Code looks like configuration, not imperative programming
- **AI-friendly**: Easier for language models to parse and generate
- **Less boilerplate**: No `ref()`, `Ref()`, or `self` parameters
- **Declarative**: Describes what you want, not how to construct it

---

## References

The domain package automatically detects references by analyzing your classes.

### Class References

Reference another resource by class name:

```python
class WebServer:
    resource: Instance
    subnet = WebSubnet        # Reference to WebSubnet
```

### Attribute References

Reference a specific attribute of another resource:

```python
class LambdaFunction:
    resource: Function
    role_arn = ExecutionRole.Arn  # Gets the Arn of ExecutionRole
```

This is useful when you need a specific output (like an ARN, ID, or endpoint) rather than a reference to the whole resource.

### Collection References

Lists and dicts can contain references:

```python
class LoadBalancer:
    resource: ALB
    subnets = [SubnetA, SubnetB, SubnetC]  # List of references

class SecurityConfig:
    resource: SecurityGroup
    rules = {
        "web": WebRule,
        "api": ApiRule,
    }  # Dict of references
```

### What's NOT a Reference

- Primitive values: `name = "my-bucket"`
- Dictionaries with primitive values: `tags = {"env": "prod"}`
- Classes from outside the domain package

---

## Multi-File Organization

Resources are typically organized across multiple files with a single import:

**`resources/__init__.py`** — Sets up the package (handled by the domain package)

**`resources/networking.py`**
```python
from . import *

class AppVPC:
    resource: VPC
    cidr_block = "10.0.0.0/16"

class WebSubnet:
    resource: Subnet
    vpc = AppVPC
    cidr_block = "10.0.1.0/24"
```

**`resources/compute.py`**
```python
from . import *

class WebServer:
    resource: Instance
    subnet = WebSubnet        # Available from networking.py
    instance_type = "t3.medium"
```

**Usage:**
```python
from resources import *

# All resources available
print(AppVPC, WebSubnet, WebServer)
```

The domain package handles:
- Loading files in dependency order (networking before compute)
- Making classes available across files
- IDE autocomplete via generated stub files

---

## Context Values

Some values are resolved at serialization or deployment time, not when you write the code:

```python
class MyBucket:
    resource: Bucket
    bucket_name = Sub("${AWS::AccountId}-app-data")
```

Common context values (depending on the domain package):
- Account/project identifiers
- Region/location
- Environment name
- Stack/deployment name

The exact syntax depends on your domain package and target platform.

---

## Output Formats

The same resource declarations can produce different output formats:

```python
class MySubnet:
    resource: Subnet
    vpc = MyVPC
    cidr_block = "10.0.1.0/24"
```

**CloudFormation-style JSON:**
```json
{
    "MySubnet": {
        "Type": "AWS::EC2::Subnet",
        "Properties": {
            "VpcId": {"Ref": "MyVPC"},
            "CidrBlock": "10.0.1.0/24"
        }
    }
}
```

**Kubernetes-style YAML:**
```yaml
apiVersion: v1
kind: Subnet
metadata:
  name: my-subnet
spec:
  vpcRef:
    name: my-vpc
  cidrBlock: 10.0.1.0/24
```

The domain package determines the output format through its provider implementation.

---

## Putting It Together

A complete example showing multiple concepts:

```python
from . import *

# Networking
class AppVPC:
    resource: VPC
    cidr_block = "10.0.0.0/16"
    enable_dns_hostnames = True

class WebSubnet:
    resource: Subnet
    vpc = AppVPC
    cidr_block = "10.0.1.0/24"
    availability_zone = Sub("${AWS::Region}a")

class WebSecurityGroup:
    resource: SecurityGroup
    vpc = AppVPC
    description = "Web server security group"

# Compute
class WebServer:
    resource: Instance
    subnet = WebSubnet
    security_groups = [WebSecurityGroup]
    instance_type = "t3.medium"
```

Notice:
- Single import at the top
- No decorators
- References are just class names
- Flat structure with simple attribute assignments

---

## Design Philosophy

| Goal | How It's Achieved |
|------|-------------------|
| **Flat** | Wrapper pattern with class attributes, no nesting |
| **Readable** | No-parens references, declarative style |
| **Type-safe** | Resource type annotations, IDE support |
| **Multi-format** | Same declarations, different outputs |

---

## Extension Points

Domain packages may provide additional features:

### Computed Values

Properties derived from other properties:

```python
class NamingConvention:
    resource: Bucket
    environment = "prod"
    app_name = "myapp"

    @computed
    def bucket_name(self):
        return f"{self.environment}-{self.app_name}-data"
```

### Conditional Values

Properties that vary based on context:

```python
class Database:
    resource: DBInstance
    multi_az = when(
        condition=IsProduction,
        then_value=True,
        else_value=False
    )
```

### Conditional Resources

Resources created only under certain conditions:

```python
class BastionHost:
    resource: Instance
    condition = EnableBastion
    instance_type = "t3.micro"
```

Check your domain package documentation for available extensions.

---

## Next Steps

- [Specification](../spec/SPECIFICATION.md) — Formal specification of the pattern
- [Internals Guide](../INTERNALS.md) — For building domain packages
