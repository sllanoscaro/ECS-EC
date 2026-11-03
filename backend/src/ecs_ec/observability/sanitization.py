"""Reject arbitrary objects before any logger, SDK, queue or serializer can retain them."""

import math


def primitives(value, depth=0):
    """Accept only bounded JSON primitives without coercion; raise fixed ValueError on rejection.

    Exact builtin types prevent user-defined conversion/iteration hooks. The schema
    separately rejects unknown fields. Depth/string/node bounds cap prevalidation work.
    """
    if depth > 4:
        raise ValueError("schema_rejected")
    if value is None or type(value) in (bool, int):
        if type(value) is int and abs(value) > 2**63 - 1:
            raise ValueError("schema_rejected")
        return
    if type(value) is float and math.isfinite(value):
        return
    if type(value) is str and len(value) <= 16384:
        return
    if type(value) is dict and len(value) <= 64:
        for key, item in value.items():
            if type(key) is not str or len(key) > 128:
                raise ValueError("schema_rejected")
            primitives(item, depth + 1)
        return
    raise ValueError("schema_rejected")
