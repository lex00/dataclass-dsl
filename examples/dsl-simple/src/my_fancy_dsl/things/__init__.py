"""
MyFancyDSL things - automatically loaded via setup_resources().

Each thing is defined in its own file and uses:
    from my_fancy_dsl.things import *

This gives access to:
- The @my_fancy_dsl decorator
- All previously-loaded thing classes (for references)
"""

from dataclass_dsl import StubConfig, setup_resources

from my_fancy_dsl import my_fancy_dsl

# Configure stub generation for IDE support
stub_config = StubConfig(
    package_name="my_fancy_dsl",
    core_imports=["my_fancy_dsl"],
)

# Load all thing modules in dependency order, injecting the decorator
setup_resources(
    __file__,
    __name__,
    globals(),
    stub_config=stub_config,
    extra_namespace={"my_fancy_dsl": my_fancy_dsl},
)
