"""Drop schema change type and SQL generation.

PostgreSQL 17 DROP SCHEMA Synopsis:
https://www.postgresql.org/docs/17/sql-dropschema.html

DROP SCHEMA [ IF EXISTS ] name [, ...] [ CASCADE | RESTRICT ]

Currently supported:
- Basic schema dropping with schema name

Intentionally Not Supported:
- IF EXISTS option
- CASCADE - pgdelta uses dependency resolution instead of CASCADE
- RESTRICT option (default behavior)
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class DropSchema:
    """Drop schema change."""

    stable_id: str
    nspname: str


def generate_drop_schema_sql(change: DropSchema) -> str:
    """Generate DROP SCHEMA SQL."""
    quoted_schema = f'"{change.nspname}"'

    # Dependency resolution handles ordering, no CASCADE needed
    return f"DROP SCHEMA {quoted_schema};"
