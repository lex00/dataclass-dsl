"""MyFancyThing1 - Base thing with no dependencies."""

from . import *  # noqa: F401, F403


@my_fancy_dsl
class MyFancyThing1:
    """Base thing demonstrating basic fields."""

    name = "thing1-default"
    value = 100
    tags = []
