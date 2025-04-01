"""Module contain types."""
from typing import _alias  # type: ignore


__all__ = (
    "MarshmallowJsonType",
)

# dirty hack to make mypy happy
MarshmallowJsonType = _alias(str, 0, name="MarshmallowJsonType")
MarshmallowJsonType.__qualname__ = "MarshmallowJsonType"
MarshmallowJsonType.__origin__ = None
