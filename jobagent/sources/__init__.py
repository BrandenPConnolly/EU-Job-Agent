from .adzuna import AdzunaSource
from .arbeitnow import ArbeitnowSource
from .jooble import JoobleSource

ALL_SOURCES = [ArbeitnowSource, JoobleSource, AdzunaSource]


def build_sources(config) -> list:
    return [cls(config) for cls in ALL_SOURCES]
