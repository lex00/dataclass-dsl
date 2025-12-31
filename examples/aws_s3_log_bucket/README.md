# AWS S3 Log Bucket Example

This example shows real output from [wetwire-aws](https://github.com/lex00/wetwire/tree/main/python/packages/wetwire-aws), a domain package built on dataclass-dsl.

## The Code

```python
from . import *

class LogBucketEncryptionDefault:
    resource: s3.bucket.ServerSideEncryptionByDefault
    sse_algorithm = s3.ServerSideEncryption.AES256

class LogBucketEncryptionRule:
    resource: s3.bucket.ServerSideEncryptionRule
    server_side_encryption_by_default = LogBucketEncryptionDefault

class LogBucketEncryption:
    resource: s3.bucket.BucketEncryption
    server_side_encryption_configuration = [LogBucketEncryptionRule]

class LogBucketPublicAccessBlock:
    resource: s3.bucket.PublicAccessBlockConfiguration
    block_public_acls = True
    block_public_policy = True
    ignore_public_acls = True
    restrict_public_buckets = True

class LogBucketVersioning:
    resource: s3.bucket.VersioningConfiguration
    status = s3.BucketVersioningStatus.ENABLED

class LogBucket:
    resource: s3.Bucket
    bucket_encryption = LogBucketEncryption
    public_access_block_configuration = LogBucketPublicAccessBlock
    versioning_configuration = LogBucketVersioning
```

## What This Demonstrates

- **Single import**: `from . import *`
- **No decorators**: Classes are plain declarations
- **Flat wrappers**: Each class wraps a resource type
- **Type-safe references**: `s3.Bucket`, `s3.bucket.BucketEncryption`, etc.
- **Enum values**: `s3.ServerSideEncryption.AES256`, `s3.BucketVersioningStatus.ENABLED`
- **Composition**: `LogBucket` references `LogBucketEncryption`, which references `LogBucketEncryptionRule`, etc.

## Building Your Own Domain Package

Anyone can build a domain package like wetwire-aws. You need:

1. **Resource type definitions** — Classes representing your target format (CloudFormation, Terraform, Kubernetes, etc.)
2. **A decorator** — Created with `create_decorator()` to handle registration and reference detection
3. **A loader** — Using `setup_resources()` to enable `from . import *`
4. **A provider** — To serialize resources to your output format

See the [Internals Guide](../../docs/INTERNALS.md) for implementation details.

## Source

This example is from: https://github.com/lex00/wetwire/tree/main/python/packages/wetwire-agent/tests/domains/aws/scenarios/s3_log_bucket/results/beginner/generated
