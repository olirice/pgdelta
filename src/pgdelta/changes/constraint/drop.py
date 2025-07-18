"""Drop constraint change type and SQL generation.

PostgreSQL constraint operations:

DROP CONSTRAINT:
ALTER TABLE table_name DROP CONSTRAINT constraint_name

Currently supported:
- DROP PRIMARY KEY constraints
- DROP UNIQUE constraints
- DROP CHECK constraints
- DROP FOREIGN KEY constraints
- DROP EXCLUSION constraints

Intentionally not supported:
- CASCADE/RESTRICT options (pgdelta handles dependency ordering)
- IF EXISTS option (pgdelta tracks existence, so always knows if constraint exists)
"""

from dataclasses import dataclass

from ...model.pg_attribute import PgAttribute
from ...model.pg_constraint import PgConstraint


@dataclass(frozen=True)
class DropConstraint:
    """Drop constraint change."""

    stable_id: str  # namespace.table.constraint_name
    constraint: PgConstraint
    table_columns: list[PgAttribute]  # All columns in the table for name resolution
    referenced_table_columns: list[PgAttribute] | None = None  # For foreign keys


def generate_drop_constraint_sql(change: DropConstraint) -> str:
    """Generate DROP CONSTRAINT SQL."""
    constraint = change.constraint
    quoted_schema = f'"{constraint.namespace_name}"'
    quoted_table = f'"{constraint.table_name}"'
    quoted_constraint_name = f'"{constraint.conname}"'

    return f"ALTER TABLE {quoted_schema}.{quoted_table} DROP CONSTRAINT {quoted_constraint_name};"
