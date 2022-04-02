# -*- coding: utf-8 -*-

from enum import Enum
from typing import Union, Optional


class BaseEnum(Enum):
    @classmethod
    def choices(cls):
        return [(e.value, e.value) for e in cls]

    @classmethod
    def values(cls):
        return [e.value for e in cls]

    def __str__(self):
        return str(self.value)

    @classmethod
    def from_value(cls, value: Union[str, int]) -> Optional['BaseEnum']:
        for tag in cls:
            if isinstance(tag.value, str) and str(tag.value).upper() == value.upper():
                return tag
            elif not isinstance(tag.value, str) and tag.value == value:
                return tag
        return None
