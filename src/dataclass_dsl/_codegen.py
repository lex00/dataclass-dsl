"""
Code generation utilities for domain packages.

Provides name conversion, escaping, and other utilities commonly needed
when generating Python code from domain-specific schemas.

Example:
    >>> from dataclass_dsl._codegen import to_snake_case, sanitize_python_name
    >>> to_snake_case("BucketName")
    'bucket_name'
    >>> sanitize_python_name("class")
    'class_'
"""

from __future__ import annotations

import re

__all__ = [
    "PYTHON_KEYWORDS",
    "to_snake_case",
    "to_pascal_case",
    "sanitize_python_name",
    "sanitize_class_name",
    "is_valid_python_identifier",
    "escape_string",
    "escape_docstring",
]

# Python keywords that require sanitization (append underscore)
PYTHON_KEYWORDS = frozenset(
    {
        "and",
        "as",
        "assert",
        "async",
        "await",
        "break",
        "case",
        "class",
        "continue",
        "def",
        "del",
        "elif",
        "else",
        "except",
        "finally",
        "for",
        "from",
        "global",
        "if",
        "import",
        "in",
        "is",
        "lambda",
        "match",
        "nonlocal",
        "not",
        "or",
        "pass",
        "raise",
        "return",
        "try",
        "type",
        "while",
        "with",
        "yield",
    }
)


def to_snake_case(name: str) -> str:
    """Convert PascalCase or camelCase to snake_case.

    Handles acronyms intelligently: VPCId becomes vpc_id, IPv6 becomes ipv6.

    Args:
        name: A string in PascalCase or camelCase.

    Returns:
        The string converted to snake_case.

    Examples:
        >>> to_snake_case("BucketName")
        'bucket_name'
        >>> to_snake_case("VPCId")
        'vpc_id'
        >>> to_snake_case("S3Key")
        's3_key'
        >>> to_snake_case("IPv6CidrBlock")
        'ipv6_cidr_block'
    """
    # Insert underscore before uppercase letters (except at start)
    result = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    # Insert underscore before uppercase in acronyms
    result = re.sub("([a-z0-9])([A-Z])", r"\1_\2", result)
    return result.lower()


def to_pascal_case(name: str) -> str:
    """Convert snake_case or space-separated string to PascalCase.

    Args:
        name: A string in snake_case, space-separated, or with special characters.

    Returns:
        The string converted to PascalCase.

    Examples:
        >>> to_pascal_case("bucket_name")
        'BucketName'
        >>> to_pascal_case("my key")
        'MyKey'
        >>> to_pascal_case("some-value")
        'SomeValue'
    """
    # Replace non-alphanumeric with spaces, then title-case each word
    cleaned = re.sub(r"[^a-zA-Z0-9]", " ", name)
    return "".join(word.title() for word in cleaned.split())


def sanitize_python_name(name: str) -> str:
    """Ensure a name is a valid Python identifier.

    If the name conflicts with a Python keyword, append an underscore.

    Args:
        name: A potential Python identifier.

    Returns:
        A valid Python identifier (original or with trailing underscore).

    Examples:
        >>> sanitize_python_name("class")
        'class_'
        >>> sanitize_python_name("lambda")
        'lambda_'
        >>> sanitize_python_name("bucket_name")
        'bucket_name'
    """
    if name in PYTHON_KEYWORDS:
        return f"{name}_"
    return name


def sanitize_class_name(name: str) -> str:
    """Ensure name is a valid Python class name.

    Some schemas allow identifiers starting with digits, but Python
    class names cannot start with digits. Prepend underscore if needed.

    Args:
        name: A potential class name.

    Returns:
        A valid Python class name.

    Examples:
        >>> sanitize_class_name("MyBucket")
        'MyBucket'
        >>> sanitize_class_name("123Resource")
        '_123Resource'
    """
    if name and name[0].isdigit():
        return f"_{name}"
    return name


def is_valid_python_identifier(name: str) -> bool:
    """Check if a name is a valid Python identifier.

    Args:
        name: The string to check.

    Returns:
        True if the name is a valid Python identifier, False otherwise.

    Examples:
        >>> is_valid_python_identifier("my_var")
        True
        >>> is_valid_python_identifier("123abc")
        False
        >>> is_valid_python_identifier("class")
        True  # Valid identifier, just a keyword
    """
    return name.isidentifier()


def escape_string(s: str) -> str:
    """Escape a string for use in Python source code.

    Handles newlines, quotes, backslashes, and other special characters.

    Args:
        s: The string to escape.

    Returns:
        An escaped string safe for inclusion in Python source.

    Examples:
        >>> escape_string('hello\\nworld')
        'hello\\\\nworld'
        >>> escape_string("it's a test")
        "it\\\\'s a test"
    """
    # Use repr() but strip the quotes
    escaped = repr(s)
    # Remove leading/trailing quotes
    if escaped.startswith("'") and escaped.endswith("'"):
        escaped = escaped[1:-1]
    elif escaped.startswith('"') and escaped.endswith('"'):
        escaped = escaped[1:-1]
    return escaped


def escape_docstring(s: str) -> str:
    """Escape a string for use in a Python docstring.

    Handles triple quotes and backslashes.

    Args:
        s: The string to escape.

    Returns:
        An escaped string safe for inclusion in a docstring.

    Examples:
        >>> escape_docstring('This is a "test"')
        'This is a "test"'
    """
    # Escape backslashes first
    s = s.replace("\\", "\\\\")
    # Escape triple quotes
    s = s.replace('"""', '\\"\\"\\"')
    return s
