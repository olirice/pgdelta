"""pgdelta: PostgreSQL schema differ and DDL generator."""

__version__ = "0.1.0"

from .catalog import PgCatalog
from .changes import DDL
from .changes.dispatcher import generate_sql
from .exceptions import (
    CyclicDependencyError,
    DependencyResolutionError,
    PgDeltaError,
)

__all__ = [
    "DDL",
    "CyclicDependencyError",
    "DependencyResolutionError",
    "PgCatalog",
    "PgDeltaError",
    "generate_sql",
]
