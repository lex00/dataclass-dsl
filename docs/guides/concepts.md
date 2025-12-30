# Core Concepts

This guide explains the fundamental concepts behind dataclass-dsl. Understanding these patterns will help you write effective declarative code and understand how the framework works.

## Table of Contents

1. [The Wrapper Pattern](#the-wrapper-pattern)
2. [The No-Parens Principle](#the-no-parens-principle)
3. [Reference Detection](#reference-detection)
4. [The Registry](#the-registry)
5. [Templates](#templates)
6. [Context](#context)
7. [Providers](#providers)
8. [Computed Values](#computed-values)
9. [Conditionals](#conditionals)

---

## The Wrapper Pattern

The core pattern in dataclass-dsl is **wrapping**: you create a class that wraps an underlying resource type.

```python
@my_decorator
class LogBucket:
    resource: Bucket           # The type being wrapped
    bucket_name = "app-logs"   # Properties of that type
```

**Why wrapping?**

1. **Naming**: Your class name (`LogBucket`) becomes the logical resource name
2. **Referencing**: Other resources refer to `LogBucket`, not a string ID
3. **Type safety**: The decorator knows what properties are valid for `Bucket`
4. **Flat structure**: All properties are class attributes, no nesting

**The `resource` field is special**: It declares what you're wrapping. It's never assigned a value — it's a type annotation that tells the decorator what kind of resource this is.

---

## The No-Parens Principle

In dataclass-dsl, references to other resources are expressed as **class names without parentheses**:

```python
@my_decorator
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

**Benefits of no-parens:**

- **Readable**: Code looks like configuration, not imperative programming
- **AI-friendly**: Easier for language models to parse and generate
- **Less boilerplate**: No `ref()`, `Ref()`, or `self` parameters
- **Declarative**: Describes what you want, not how to construct it

---

## Reference Detection

The decorator automatically detects references by analyzing your class. It recognizes:

### Class References

When a class attribute's value is another decorated class:

```python
@my_decorator
class WebServer:
    resource: Instance
    subnet = WebSubnet        # Detected as Ref[WebSubnet]
```

### Attribute References

When you access an attribute of a decorated class:

```python
@my_decorator
class LambdaFunction:
    resource: Function
    role = ExecutionRole.Arn  # Detected as Attr[ExecutionRole, "Arn"]
```

### Collection References

Lists and dicts containing references:

```python
@my_decorator
class LoadBalancer:
    resource: ALB
    subnets = [SubnetA, SubnetB, SubnetC]  # List of references

@my_decorator
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
- External classes (not decorated)

---

## The Registry

Every decorated class is automatically registered when it's defined. The registry tracks:

- All resource classes
- Their resource types
- Their module/package location

```python
# These classes register themselves automatically
@my_decorator
class MyVPC:
    resource: VPC
    cidr_block = "10.0.0.0/16"

@my_decorator
class MySubnet:
    resource: Subnet
    vpc = MyVPC
    cidr_block = "10.0.1.0/24"

# Later, collect all resources from the registry
template = Template.from_registry()
```

### Scoped Discovery

You can limit discovery to specific packages:

```python
# Only collect resources from 'my_stack.networking'
template = Template.from_registry(
    scope_package="my_stack.networking"
)
```

This is useful for:
- Generating separate templates per module
- Excluding test resources
- Multi-stack architectures

---

## Templates

A Template aggregates resources from the registry and serializes them to output formats.

```python
# Collect all registered resources
template = Template.from_registry()

# Generate output
yaml_output = template.to_yaml()
json_output = template.to_json()
dict_output = template.to_dict()
```

Templates handle:
- Collecting resources from the registry
- Resolving references between resources
- Ordering resources by dependencies
- Serializing to the target format

### Template Sections

Domain templates may have additional sections:

```python
# Domain-specific templates may support parameters, outputs, etc.
template = DomainTemplate.from_registry(
    parameters=[EnvironmentParam, InstanceTypeParam],
    outputs=[VpcIdOutput, SubnetIdsOutput],
)
```

---

## Context

Context provides values that are resolved at serialization time, not definition time. This is useful for:

- Environment-specific values
- Platform pseudo-parameters
- Dynamic values like account IDs

```python
@my_decorator
class MyBucket:
    resource: Bucket
    bucket_name = Sub("${AccountId}-app-data")
```

When serialized, pseudo-parameters are resolved by the target platform at deployment time.

---

## Providers

Providers handle format-specific serialization. The same resource declaration can produce different outputs:

```python
# Same declaration
@my_decorator
class MySubnet:
    resource: Subnet
    vpc = MyVPC
    cidr_block = "10.0.1.0/24"
```

**JSON output (example):**
```json
{
    "MySubnet": {
        "Type": "Subnet",
        "Properties": {
            "VpcId": {"Ref": "MyVPC"},
            "CidrBlock": "10.0.1.0/24"
        }
    }
}
```

**YAML output (example):**
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

Providers define how to serialize:
- References
- Attribute references
- The overall template structure

---

## Computed Values

Sometimes a property should be derived from other properties. Use `@computed`:

```python
@my_decorator
class NamingConvention:
    resource: Bucket
    environment = "prod"
    app_name = "myapp"

    @computed
    def bucket_name(self):
        return f"{self.environment}-{self.app_name}-data"
```

Computed values:
- Are calculated at serialization time
- Can reference other properties on the same class
- Can reference context values
- Are read-only (no setter)

---

## Conditionals

dataclass-dsl supports conditional resource creation and property values.

### Conditional Properties

Use `when()` to conditionally set a property:

```python
@my_decorator
class Database:
    resource: DBInstance
    multi_az = when(
        condition=IsProduction,
        then_value=True,
        else_value=False
    )
```

### Conditional Resources

Resources can be conditionally created:

```python
@my_decorator
class BastionHost:
    resource: Instance
    condition = EnableBastion  # Only created if EnableBastion is true
    instance_type = "t3.micro"
```

### Pattern Matching

For multiple conditions, use `match()`:

```python
@my_decorator
class WebServer:
    resource: Instance
    instance_type = match(
        (Environment == "prod", "c5.xlarge"),
        (Environment == "staging", "c5.large"),
        default="t3.medium"
    )
```

---

## Putting It Together

Here's a complete example showing multiple concepts:

```python
from my_domain import my_decorator, Sub

# Base networking
@my_decorator
class AppVPC:
    resource: VPC
    cidr_block = "10.0.0.0/16"
    enable_dns_hostnames = True

@my_decorator
class WebSubnet:
    resource: Subnet
    vpc_id = AppVPC                   # Reference (no-parens)
    cidr_block = "10.0.1.0/24"
    availability_zone = Sub("${Region}a")  # Context via Sub()

@my_decorator
class WebSecurityGroup:
    resource: SecurityGroup
    vpc_id = AppVPC                   # Reference (no-parens)
    group_description = "Web server security group"

# Compute
@my_decorator
class WebServer:
    resource: Instance
    subnet_id = WebSubnet             # Reference (no-parens)
    security_group_ids = [WebSecurityGroup]  # List of references
    instance_type = "t3.medium"

# Generate template
template = Template.from_registry()
output = template.to_yaml()
```

---

## Design Philosophy

These concepts work together to achieve dataclass-dsl's goals:

| Goal | How It's Achieved |
|------|-------------------|
| **Flat** | Wrapper pattern with class attributes, no nesting |
| **Type-safe** | Resource types, reference detection, IDE support |
| **Readable** | No-parens references, declarative style |
| **Multi-format** | Provider abstraction, domain-specific templates |

## Next Steps

- [SPECIFICATION.md](../spec/SPECIFICATION.md) — Formal specification
