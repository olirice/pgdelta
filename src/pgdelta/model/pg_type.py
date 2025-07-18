"""PostgreSQL type model."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy import text

from pgdelta.model.base import BasePgModel, field_data, field_identity, field_internal

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


@dataclass(frozen=True)
class CompositeAttribute:
    """Represents a single attribute in a composite type."""

    name: str
    type_name: str
    position: int
    not_null: bool


@dataclass(slots=True, frozen=True)
class PgType(BasePgModel):
    """PostgreSQL type model."""

    # Internal fields
    oid: int = field_internal()

    # Identity fields
    typname: str = field_identity()
    namespace: str = field_identity()  # From pg_namespace join

    # Data fields
    typtype: str = field_data()  # 'b'=base, 'c'=composite, 'd'=domain, 'e'=enum, 'p'=pseudo, 'r'=range, 'm'=multirange
    typlen: int = field_data()
    typbyval: bool = field_data()
    typcategory: str = field_data()
    typisdefined: bool = field_data()
    typdelim: str = field_data()

    # Function references (stored as OIDs) - these are internal PostgreSQL references
    typinput: int = field_internal()
    typoutput: int = field_internal()
    typreceive: int = field_internal()
    typsend: int = field_internal()

    # Type-specific internal references (OIDs that vary between databases)
    typelem: int | None = field_internal(default=None)  # Element type OID for arrays
    typarray: int | None = field_internal(default=None)  # Array type OID
    typrelid: int | None = field_internal(
        default=None
    )  # Related table OID for composite types

    # Additional metadata for specific type categories
    enum_values: list[str] | None = field_data(default=None)  # For enum types
    domain_base_type: str | None = field_data(default=None)  # For domain types
    domain_constraints: list[str] | None = field_data(default=None)  # For domain types
    composite_attributes: list[CompositeAttribute] | None = field_data(
        default=None
    )  # For composite types
    range_subtype: str | None = field_data(default=None)  # For range types
    multirange_range_type: str | None = field_data(default=None)  # For multirange types

    @property
    def stable_id(self) -> str:
        """Database-portable stable identifier."""
        return f"type:{self.namespace}.{self.typname}"

    @property
    def pg_depend_id(self) -> str:
        """PostgreSQL pg_depend format identifier."""
        return f"1247.{self.oid}.0"  # 1247 is pg_type's classid


def extract_types(session: Session, namespace_oids: list[int]) -> list[PgType]:
    """Extract user-defined types from pg_type."""
    if not namespace_oids:
        return []

    # Query to extract user-defined types with namespace information
    query = text("""
        SELECT
            t.oid,
            t.typname,
            n.nspname as namespace,
            t.typtype,
            t.typlen,
            t.typbyval,
            t.typcategory,
            t.typisdefined,
            t.typdelim,
            t.typelem,
            t.typarray,
            t.typrelid,
            t.typinput,
            t.typoutput,
            t.typreceive,
            t.typsend
        FROM pg_catalog.pg_type t
        JOIN pg_catalog.pg_namespace n ON t.typnamespace = n.oid
        WHERE t.typnamespace = ANY(:namespace_oids)
        AND t.typtype IN ('e', 'd', 'c', 'r')  -- Only user-defined types (exclude 'm' for multirange)
        AND t.typisdefined = true  -- Only fully defined types
        AND NOT (t.typtype = 'c' AND t.typrelid != 0 AND EXISTS (
            SELECT 1 FROM pg_catalog.pg_class c
            WHERE c.oid = t.typrelid AND c.relkind = 'r'
        ))  -- Exclude composite types that are created for regular tables
        AND NOT EXISTS (
            SELECT 1 FROM pg_catalog.pg_depend d
            WHERE d.classid = 1247  -- pg_type
            AND d.objid = t.oid
            AND d.deptype = 'i'  -- internal dependency (auto-generated)
        )
        ORDER BY n.nspname, t.typname
    """)

    result = session.execute(query, {"namespace_oids": namespace_oids})
    types = []

    for row in result:
        # Initialize type-specific fields
        enum_values = None
        domain_base_type = None
        domain_constraints = None
        composite_attributes = None
        range_subtype = None
        multirange_range_type = None

        # Extract additional metadata based on type category
        if row.typtype == "e":  # Enum type
            enum_values = _extract_enum_values(session, row.oid)
        elif row.typtype == "d":  # Domain type
            domain_base_type, domain_constraints = _extract_domain_info(
                session, row.oid
            )
        elif row.typtype == "c":  # Composite type
            composite_attributes = _extract_composite_attributes(session, row.oid)
        elif row.typtype == "r":  # Range type
            range_subtype = _extract_range_subtype(session, row.oid)
        elif row.typtype == "m":  # Multirange type
            multirange_range_type = _extract_multirange_range_type(session, row.oid)

        pg_type = PgType(
            oid=row.oid,
            typname=row.typname,
            namespace=row.namespace,
            typtype=row.typtype,
            typlen=row.typlen,
            typbyval=row.typbyval,
            typcategory=row.typcategory,
            typisdefined=row.typisdefined,
            typdelim=row.typdelim,
            typelem=row.typelem,
            typarray=row.typarray,
            typrelid=row.typrelid,
            typinput=row.typinput,
            typoutput=row.typoutput,
            typreceive=row.typreceive,
            typsend=row.typsend,
            enum_values=enum_values,
            domain_base_type=domain_base_type,
            domain_constraints=domain_constraints,
            composite_attributes=composite_attributes,
            range_subtype=range_subtype,
            multirange_range_type=multirange_range_type,
        )
        types.append(pg_type)

    return types


def _extract_enum_values(session: Session, type_oid: int) -> list[str]:
    """Extract enum values for an enum type."""
    query = text("""
        SELECT enumlabel
        FROM pg_catalog.pg_enum
        WHERE enumtypid = :type_oid
        ORDER BY enumsortorder
    """)

    result = session.execute(query, {"type_oid": type_oid})
    return [row.enumlabel for row in result]


def _extract_domain_info(
    session: Session, type_oid: int
) -> tuple[str | None, list[str] | None]:
    """Extract base type and constraints for a domain type."""
    # Get base type
    base_type_query = text("""
        SELECT format_type(typbasetype, typtypmod) as base_type
        FROM pg_catalog.pg_type
        WHERE oid = :type_oid
    """)

    base_result = session.execute(base_type_query, {"type_oid": type_oid})
    base_row = base_result.fetchone()
    base_type = base_row.base_type if base_row else None

    # Get constraints using pg_get_constraintdef() for compatibility with all PostgreSQL versions
    constraints_query = text("""
        SELECT pg_catalog.pg_get_constraintdef(oid) as constraint_def
        FROM pg_catalog.pg_constraint
        WHERE contypid = :type_oid
        ORDER BY conname
    """)

    constraints_result = session.execute(constraints_query, {"type_oid": type_oid})
    constraints = [
        row.constraint_def for row in constraints_result if row.constraint_def
    ]

    return base_type, constraints if constraints else None


def _extract_composite_attributes(
    session: Session, type_oid: int
) -> list[CompositeAttribute] | None:
    """Extract attributes for a composite type."""
    query = text("""
        SELECT
            a.attname,
            format_type(a.atttypid, a.atttypmod) as atttype,
            a.attnum,
            a.attnotnull
        FROM pg_catalog.pg_attribute a
        WHERE a.attrelid = (
            SELECT typrelid FROM pg_catalog.pg_type WHERE oid = :type_oid
        )
        AND a.attnum > 0
        AND NOT a.attisdropped
        ORDER BY a.attnum
    """)

    result = session.execute(query, {"type_oid": type_oid})
    attributes = []

    for row in result:
        attributes.append(
            CompositeAttribute(
                name=row.attname,
                type_name=row.atttype,
                position=row.attnum,
                not_null=row.attnotnull,
            )
        )

    return attributes if attributes else None


def _extract_range_subtype(session: Session, type_oid: int) -> str | None:
    """Extract subtype information for a range type."""
    query = text("""
        SELECT format_type(rngsubtype, 0) as subtype
        FROM pg_catalog.pg_range
        WHERE rngtypid = :type_oid
    """)

    result = session.execute(query, {"type_oid": type_oid})
    row = result.fetchone()
    return row.subtype if row else None


def _extract_multirange_range_type(session: Session, type_oid: int) -> str | None:
    """Extract range type information for a multirange type."""
    query = text("""
        SELECT n.nspname || '.' || t.typname as range_type
        FROM pg_catalog.pg_range r
        JOIN pg_catalog.pg_type t ON r.rngtypid = t.oid
        JOIN pg_catalog.pg_namespace n ON t.typnamespace = n.oid
        WHERE r.rngmultitypid = :type_oid
    """)

    result = session.execute(query, {"type_oid": type_oid})
    row = result.fetchone()
    return row.range_type if row else None
