"""PostgreSQL constraint catalog model (pg_constraint)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy import text
from sqlalchemy.orm import Session

from .base import BasePgModel, field_data, field_identity, field_internal

if TYPE_CHECKING:
    pass


@dataclass(slots=True, frozen=True)
class PgConstraint(BasePgModel):
    """
    PostgreSQL constraint representation from pg_constraint.

    Maps to PostgreSQL system catalog pg_constraint which stores check constraints,
    primary key, unique, foreign key, and exclusion constraints on tables.
    """

    # Identity fields (uniquely identify a constraint)
    conname: str = field_identity()  # Constraint name
    namespace_name: str = field_identity()  # Schema name
    table_name: str = field_identity()  # Table name

    # Data fields (define constraint properties)
    contype: str = field_data()  # Constraint type: c=check, f=foreign key, p=primary key, u=unique, t=trigger, x=exclusion
    condeferrable: bool = field_data()  # Is constraint deferrable?
    condeferred: bool = field_data()  # Is constraint initially deferred?
    convalidated: bool = field_data()  # Is constraint validated?
    confupdtype: str = field_data()  # Foreign key update action: a=no action, r=restrict, c=cascade, n=set null, d=set default
    confdeltype: str = field_data()  # Foreign key delete action: a=no action, r=restrict, c=cascade, n=set null, d=set default
    confmatchtype: str = (
        field_data()
    )  # Foreign key match type: f=full, p=partial, s=simple (default)
    conislocal: bool = field_data()  # True if constraint is defined locally
    coninhcount: int = (
        field_data()
    )  # Number of direct inheritance ancestors that have this constraint
    connoinherit: bool = field_data()  # True if constraint is non-inheritable
    conkey: list[int] = (
        field_data()
    )  # Column numbers that the constraint constrains (empty if not column constraint)
    confkey: list[int] = (
        field_data()
    )  # Foreign key referenced column numbers (empty if not foreign key)
    conbin: str | None = (
        field_data()
    )  # Check constraint expression (nodeToString representation)
    conpredicate: str | None = (
        field_data()
    )  # Partial constraint WHERE clause expression

    # Internal fields (PostgreSQL internals)
    oid: int = field_internal()
    connamespace: int = field_internal()  # Namespace OID
    conrelid: int = field_internal()  # Table OID
    contypid: int = (
        field_internal()
    )  # Domain this constraint is on (0 if not domain constraint)
    conindid: int = (
        field_internal()
    )  # Index supporting this constraint (0 if not needed)
    conparentid: int = (
        field_internal()
    )  # Corresponding constraint in parent partitioned table
    confrelid: int = (
        field_internal()
    )  # Referenced table for foreign key (0 if not foreign key)
    conpfeqop: list[int] = field_internal()  # Foreign key PK = FK operator OIDs
    conppeqop: list[int] = field_internal()  # Foreign key PK = PK operator OIDs
    conffeqop: list[int] = field_internal()  # Foreign key FK = FK operator OIDs
    conexclop: list[int] = field_internal()  # Exclusion constraint operator OIDs

    @property
    def stable_id(self) -> str:
        """Cross-database portable identifier: namespace.table.constraint_name."""
        return f"{self.namespace_name}.{self.table_name}.{self.conname}"

    @property
    def table_stable_id(self) -> str:
        """Stable ID of the table this constraint belongs to."""
        return f"r:{self.namespace_name}.{self.table_name}"

    @property
    def constraint_type_name(self) -> str:
        """Human-readable constraint type name."""
        type_map = {
            "c": "CHECK",
            "f": "FOREIGN KEY",
            "p": "PRIMARY KEY",
            "u": "UNIQUE",
            "t": "TRIGGER",
            "x": "EXCLUSION",
        }
        return type_map.get(self.contype, f"UNKNOWN({self.contype})")


def extract_constraints(session: Session) -> list[PgConstraint]:
    """
    Extract constraints from PostgreSQL pg_constraint catalog.

    Returns a list of PgConstraint objects.
    """
    query = text("""
        SELECT
            c.oid,
            c.conname,
            c.connamespace,
            c.conrelid,
            c.contype,
            c.condeferrable,
            c.condeferred,
            c.convalidated,
            c.contypid,
            c.conindid,
            c.conparentid,
            c.confrelid,
            c.confupdtype,
            c.confdeltype,
            c.confmatchtype,
            c.conislocal,
            c.coninhcount,
            c.connoinherit,
            c.conkey,
            c.confkey,
            c.conpfeqop,
            c.conppeqop,
            c.conffeqop,
            c.conexclop,
            CASE
                WHEN c.contype = 'c' THEN
                    -- For CHECK constraints, extract just the expression part from pg_get_constraintdef
                    substring(pg_get_constraintdef(c.oid) from 'CHECK \\((.*)\\)$')
                ELSE c.conbin::text
            END as conbin,
            -- Extract partial constraint predicate (WHERE clause) if present
            -- Note: conpredicate field was added in PostgreSQL 12.0
            NULL as conpredicate,
            n.nspname as namespace_name,
            r.relname as table_name
        FROM pg_constraint c
        JOIN pg_class r ON c.conrelid = r.oid
        JOIN pg_namespace n ON r.relnamespace = n.oid
        WHERE r.relkind = 'r'  -- Only table constraints, not domain constraints
        AND n.nspname NOT IN ('information_schema', 'pg_catalog', 'pg_toast')
        AND n.nspname NOT LIKE 'pg_%'  -- Filter out additional PostgreSQL system schemas
        AND r.relname NOT LIKE 'pg_%'  -- Filter out PostgreSQL system tables
        ORDER BY n.nspname, r.relname, c.conname
    """)

    constraints = []
    for row in session.execute(query):
        constraint = PgConstraint(
            oid=row.oid,
            conname=row.conname,
            connamespace=row.connamespace,
            conrelid=row.conrelid,
            contype=row.contype,
            condeferrable=row.condeferrable,
            condeferred=row.condeferred,
            convalidated=row.convalidated,
            contypid=row.contypid,
            conindid=row.conindid,
            conparentid=row.conparentid,
            confrelid=row.confrelid,
            confupdtype=row.confupdtype,
            confdeltype=row.confdeltype,
            confmatchtype=row.confmatchtype,
            conislocal=row.conislocal,
            coninhcount=row.coninhcount,
            connoinherit=row.connoinherit,
            conkey=list(row.conkey) if row.conkey else [],
            confkey=list(row.confkey) if row.confkey else [],
            conpfeqop=list(row.conpfeqop) if row.conpfeqop else [],
            conppeqop=list(row.conppeqop) if row.conppeqop else [],
            conffeqop=list(row.conffeqop) if row.conffeqop else [],
            conexclop=list(row.conexclop) if row.conexclop else [],
            conbin=row.conbin,
            conpredicate=row.conpredicate,
            namespace_name=row.namespace_name,
            table_name=row.table_name,
        )
        constraints.append(constraint)

    return constraints
