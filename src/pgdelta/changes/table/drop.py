"""Drop table change type and SQL generation.

PostgreSQL 17 DROP TABLE Synopsis:
https://www.postgresql.org/docs/17/sql-droptable.html

DROP TABLE [ IF EXISTS ] name [, ...] [ CASCADE | RESTRICT ]

Currently supported:
- Basic table dropping with schema-qualified names

Intentionally not supported (not needed for DDL generation):
- IF EXISTS clause (pgdelta tracks existence, so always knows if table exists)
- CASCADE option (dependency resolution handles ordering, making CASCADE unnecessary)
- RESTRICT option (default PostgreSQL behavior, handled by dependency resolution)
- Dropping multiple tables in one statement (handled by generating separate statements)
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class DropTable:
    """Drop table change."""

    stable_id: str
    namespace: str
    relname: str


def generate_drop_table_sql(change: DropTable) -> str:
    """Generate DROP TABLE SQL."""
    quoted_schema = f'"{change.namespace}"'
    quoted_table = f'"{change.relname}"'

    return f"DROP TABLE {quoted_schema}.{quoted_table};"
