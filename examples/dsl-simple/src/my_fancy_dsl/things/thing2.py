"""MyFancyThing2 - Depends on MyFancyThing1."""

from . import *  # noqa: F401, F403


@my_fancy_dsl
class MyFancyThing2:
    """Thing demonstrating no-parens references to Thing1."""

    name = "thing2-default"
    enabled = True
    parent = MyFancyThing1  # noqa: F405
    parent_id = MyFancyThing1.Id  # noqa: F405
