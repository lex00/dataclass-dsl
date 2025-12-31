# Storage components for S3 bucket configuration.
#
# Note: These classes are in a separate file from LogBucket to demonstrate
# cross-file references. The `from . import *` pattern allows bucket.py
# to reference these classes without explicit imports.

from . import *  # noqa: F403, F405


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
