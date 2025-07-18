"""Alter constraint change type and SQL generation.

PostgreSQL constraint alteration:

ALTER CONSTRAINT (for foreign keys only):
ALTER TABLE table_name ALTER CONSTRAINT constraint_name
  [ DEFERRABLE | NOT DEFERRABLE ] [ INITIALLY DEFERRED | INITIALLY IMMEDIATE ]

Note: PostgreSQL only allows ALTER CONSTRAINT on foreign key constraints.
Other constraint types require DROP + CREATE operations (handled by diff engine).

Currently supported:
- ALTER foreign key deferrability (DEFERRABLE/NOT DEFERRABLE)
- ALTER foreign key initial mode (INITIALLY DEFERRED/INITIALLY IMMEDIATE)

Not yet supported:
- Constraint validation (VALIDATE CONSTRAINT)
"""

from dataclasses import dataclass

from ...model.pg_attribute import PgAttribute
from ...model.pg_constraint import PgConstraint


@dataclass(frozen=True)
class AlterConstraint:
    """Alter constraint change (for foreign keys only)."""

    stable_id: str  # namespace.table.constraint_name
    old_constraint: PgConstraint
    new_constraint: PgConstraint
    table_columns: list[PgAttribute]
    referenced_table_columns: list[PgAttribute] | None = None


def generate_alter_constraint_sql(change: AlterConstraint) -> str:
    """Generate ALTER CONSTRAINT SQL (foreign keys only)."""
    if change.new_constraint.contype != "f":
        raise ValueError(
            f"ALTER CONSTRAINT only supported for foreign key constraints, got {change.new_constraint.contype}"
        )

    constraint = change.new_constraint
    quoted_schema = f'"{constraint.namespace_name}"'
    quoted_table = f'"{constraint.table_name}"'
    quoted_constraint_name = f'"{constraint.conname}"'

    # Build the ALTER CONSTRAINT clause
    alter_parts = []

    # Handle deferrability
    if change.old_constraint.condeferrable != change.new_constraint.condeferrable:
        if change.new_constraint.condeferrable:
            alter_parts.append("DEFERRABLE")
        else:
            alter_parts.append("NOT DEFERRABLE")

    # Handle initial deferred state
    if change.old_constraint.condeferred != change.new_constraint.condeferred:
        if change.new_constraint.condeferred:
            alter_parts.append("INITIALLY DEFERRED")
        else:
            alter_parts.append("INITIALLY IMMEDIATE")

    if not alter_parts:
        raise ValueError(f"No changes detected for constraint {constraint.conname}")

    return f"ALTER TABLE {quoted_schema}.{quoted_table} ALTER CONSTRAINT {quoted_constraint_name} {' '.join(alter_parts)};"
