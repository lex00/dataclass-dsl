# Storage components for S3 bucket configuration.
#
# Note: These classes are in a separate file from LogBucket to demonstrate
# cross-file references. The `from . import *` pattern allows bucket.py
# to reference these classes without explicit imports.

from . import *  # noqa: F403, F405


class LogBucketEncryptionDefault(s3.Bucket.ServerSideEncryptionByDefault):
    sse_algorithm = s3.ServerSideEncryption.AES256


class LogBucketEncryptionRule(s3.Bucket.ServerSideEncryptionRule):
    server_side_encryption_by_default = LogBucketEncryptionDefault


class LogBucketEncryption(s3.Bucket.BucketEncryption):
    server_side_encryption_configuration = [LogBucketEncryptionRule]


class LogBucketPublicAccessBlock(s3.Bucket.PublicAccessBlockConfiguration):
    block_public_acls = True
    block_public_policy = True
    ignore_public_acls = True
    restrict_public_buckets = True


class LogBucketVersioning(s3.Bucket.VersioningConfiguration):
    status = s3.BucketVersioningStatus.ENABLED
