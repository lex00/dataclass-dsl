"""MyFancyThing3 - Depends on MyFancyThing2."""

from . import *  # noqa: F401, F403


@my_fancy_dsl
class MyFancyThing3:
    """Thing demonstrating no-parens references to Thing2."""

    name = "thing3-default"
    config = {}
    count = 0
    source = MyFancyThing2  # noqa: F405
    source_id = MyFancyThing2.Id  # noqa: F405
