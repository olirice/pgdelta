"""PostgreSQL catalog snapshot and extraction."""

from __future__ import annotations

import logging
from dataclasses import dataclass, fields
from typing import TYPE_CHECKING

from flupy import flu
from sqlalchemy.orm import Session

from pgdelta.model.base import BasePgModel

from .model import (
    PgAttribute,
    PgClass,
    PgConstraint,
    PgDepend,
    PgIndex,
    PgNamespace,
    PgPolicy,
    PgProc,
    PgSequence,
    PgTrigger,
    PgType,
)
from .model.pg_attribute import extract_attributes
from .model.pg_class import extract_classes
from .model.pg_constraint import extract_constraints
from .model.pg_depend import (
    extract_depends,
    extract_view_dependencies_as_pg_depend,
)
from .model.pg_index import extract_indexes
from .model.pg_namespace import extract_namespaces
from .model.pg_policy import extract_policies
from .model.pg_proc import extract_procedures
from .model.pg_sequence import extract_sequences
from .model.pg_trigger import extract_triggers
from .model.pg_type import extract_types

if TYPE_CHECKING:
    from .changes.dispatcher import DDL

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PgCatalog:
    """Immutable PostgreSQL catalog snapshot."""

    namespaces: dict[str, PgNamespace]  # Keyed by stable_id (nspname)
    classes: dict[str, PgClass]  # Keyed by stable_id (relkind:namespace.relname)
    attributes: dict[str, PgAttribute]  # Keyed by stable_id (namespace.table.column)
    constraints: dict[
        str, PgConstraint
    ]  # Keyed by stable_id (namespace.table.constraint_name)
    indexes: dict[str, PgIndex]  # Keyed by stable_id (i:namespace.index_name)
    sequences: dict[str, PgSequence]  # Keyed by stable_id (S:namespace.seqname)
    policies: dict[str, PgPolicy]  # Keyed by stable_id (P:namespace.table.policy)
    procedures: dict[
        str, PgProc
    ]  # Keyed by stable_id (function:namespace.name(argtypes))
    triggers: dict[str, PgTrigger]  # Keyed by stable_id (trigger:namespace.table.name)
    types: dict[str, PgType]  # Keyed by stable_id (type:namespace.typename)
    depends: list[PgDepend]  # All dependencies

    def diff(self, branch: PgCatalog) -> list[DDL]:
        """Generate changes to transform this catalog to the branch catalog."""
        from .diff.orchestrator import diff_catalogs

        return diff_catalogs(self, branch)

    def get_class_attributes(self, class_stable_id: str) -> list[PgAttribute]:
        """Get all attributes for a class (table/view/etc)."""
        attributes = []
        for attr in self.attributes.values():
            if attr.class_stable_id == class_stable_id:
                attributes.append(attr)

        # Sort by column number for consistent ordering
        return sorted(attributes, key=lambda col: col.attnum)

    def semantically_equals(self, other: PgCatalog) -> bool:
        """
        Check if two catalogs are semantically equal.

        This compares the logical structure of the database catalogs,
        ignoring implementation details like OIDs, file nodes, and statistics.
        """

        def _compare(left: BasePgModel | None, right: BasePgModel | None) -> bool:
            if left is None or right is None:
                return False
            return left.semantic_equality(right)

        def _key(item: BasePgModel) -> str:
            return item.__class__.__name__ + item.stable_id

        left_entities: list[BasePgModel] = []
        right_entities: list[BasePgModel] = []
        for field in fields(self):
            # We don't need to compare dependencies
            if field.name != "depends":
                field_values = getattr(self, field.name).values()
                other_field_values = getattr(other, field.name).values()

                left_entities += field_values
                right_entities += other_field_values

        return (
            flu(left_entities)
            .join_full(
                right_entities,
                key=_key,
                other_key=_key,
            )
            .map(lambda x: _compare(x[0], x[1]))
            .filter(lambda x: not x)
            .first(default=None)
        ) is None


def catalog(
    *,
    namespaces: list[PgNamespace] | None = None,
    classes: list[PgClass] | None = None,
    attributes: list[PgAttribute] | None = None,
    constraints: list[PgConstraint] | None = None,
    indexes: list[PgIndex] | None = None,
    sequences: list[PgSequence] | None = None,
    policies: list[PgPolicy] | None = None,
    procedures: list[PgProc] | None = None,
    triggers: list[PgTrigger] | None = None,
    types: list[PgType] | None = None,
    depends: list[PgDepend] | None = None,
) -> PgCatalog:
    """Create a catalog with typed arguments and stable_id mappings."""
    # Convert lists to stable_id mappings
    namespaces_dict = {}
    if namespaces:
        for namespace in namespaces:
            namespaces_dict[namespace.stable_id] = namespace

    classes_dict = {}
    if classes:
        for cls in classes:
            classes_dict[cls.stable_id] = cls

    attributes_dict = {}
    if attributes:
        for attr in attributes:
            attributes_dict[attr.stable_id] = attr

    constraints_dict = {}
    if constraints:
        for constraint in constraints:
            constraints_dict[constraint.stable_id] = constraint

    indexes_dict = {}
    if indexes:
        for index in indexes:
            indexes_dict[index.stable_id] = index

    sequences_dict = {}
    if sequences:
        for sequence in sequences:
            sequences_dict[sequence.stable_id] = sequence

    policies_dict = {}
    if policies:
        for policy in policies:
            policies_dict[policy.stable_id] = policy

    procedures_dict = {}
    if procedures:
        for procedure in procedures:
            procedures_dict[procedure.stable_id] = procedure

    triggers_dict = {}
    if triggers:
        for trigger in triggers:
            triggers_dict[trigger.stable_id] = trigger

    types_dict = {}
    if types:
        for typ in types:
            types_dict[typ.stable_id] = typ

    depends_list = depends or []

    return PgCatalog(
        namespaces=namespaces_dict,
        classes=classes_dict,
        attributes=attributes_dict,
        constraints=constraints_dict,
        indexes=indexes_dict,
        sequences=sequences_dict,
        policies=policies_dict,
        procedures=procedures_dict,
        triggers=triggers_dict,
        types=types_dict,
        depends=depends_list,
    )


def extract_catalog(session: Session) -> PgCatalog:
    """Extract catalog from PostgreSQL database session."""
    # Extract namespaces (schemas)
    namespaces = extract_namespaces(session)

    # Extract classes (tables, views, etc.)
    classes = extract_classes(session)

    # Extract attributes (columns)
    attributes = extract_attributes(session)

    # Extract constraints
    constraints = extract_constraints(session)

    # Extract indexes
    indexes = extract_indexes(session)

    # Extract sequences
    sequences = extract_sequences(session)

    # Extract RLS policies
    policies = extract_policies(session)

    # Extract procedures/functions
    procedures = extract_procedures(session)

    # Extract triggers
    triggers = extract_triggers(session)

    # Extract types
    namespace_oids = [ns.oid for ns in namespaces]
    types = extract_types(session, namespace_oids)

    # Extract dependencies from pg_depend
    depends = extract_depends(
        session,
        namespaces,
        classes,
        constraints,
        indexes,
        sequences,
        policies,
        procedures,
        triggers,
        types,
    )

    # Extract view dependencies from pg_rewrite and add them to depends list
    view_deps = extract_view_dependencies_as_pg_depend(session, classes)
    depends.extend(view_deps)

    return catalog(
        namespaces=namespaces,
        classes=classes,
        attributes=attributes,
        constraints=constraints,
        indexes=indexes,
        sequences=sequences,
        policies=policies,
        procedures=procedures,
        triggers=triggers,
        types=types,
        depends=depends,
    )
