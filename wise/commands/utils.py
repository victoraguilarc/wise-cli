# -*- coding: utf-8 -*-

from enum import Enum


class BaseEnum(Enum):
    @classmethod
    def choices(cls):
        return [(e.value, e.value) for e in cls]

    @classmethod
    def values(cls):
        return [e.value for e in cls]

    def __str__(self):
        return str(self.value)