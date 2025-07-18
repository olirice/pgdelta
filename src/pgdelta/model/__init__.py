"""PostgreSQL catalog models."""

from .base import BasePgModel
from .pg_attribute import PgAttribute, extract_attributes
from .pg_class import PgClass, extract_classes
from .pg_constraint import PgConstraint, extract_constraints
from .pg_depend import PgDepend, extract_depends
from .pg_index import PgIndex, extract_indexes
from .pg_namespace import PgNamespace, extract_namespaces
from .pg_policy import PgPolicy, extract_policies
from .pg_proc import PgProc, extract_procedures
from .pg_sequence import PgSequence, extract_sequences
from .pg_trigger import PgTrigger, extract_triggers
from .pg_type import PgType, extract_types

__all__ = [
    "BasePgModel",
    "PgAttribute",
    "PgClass",
    "PgConstraint",
    "PgDepend",
    "PgIndex",
    "PgNamespace",
    "PgPolicy",
    "PgProc",
    "PgSequence",
    "PgTrigger",
    "PgType",
    "extract_attributes",
    "extract_classes",
    "extract_constraints",
    "extract_depends",
    "extract_indexes",
    "extract_namespaces",
    "extract_policies",
    "extract_procedures",
    "extract_sequences",
    "extract_triggers",
    "extract_types",
]
