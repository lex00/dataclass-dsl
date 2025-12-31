# Main S3 bucket resource.
#
# Note: This class is in a separate file from its dependencies to demonstrate
# cross-file references. LogBucketEncryption, LogBucketPublicAccessBlock, and
# LogBucketVersioning are defined in storage.py but available here via
# `from . import *` — no explicit imports needed.

from . import *  # noqa: F403, F405


class LogBucket:
    resource: s3.Bucket
    bucket_encryption = LogBucketEncryption
    public_access_block_configuration = LogBucketPublicAccessBlock
    versioning_configuration = LogBucketVersioning
