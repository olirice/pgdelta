"""Drop view change type and SQL generation.

PostgreSQL 17 DROP VIEW Synopsis:
https://www.postgresql.org/docs/17/sql-dropview.html

DROP VIEW [ IF EXISTS ] name [, ...] [ CASCADE | RESTRICT ]

Currently supported:
- Basic view dropping with schema-qualified names

Intentionally not supported (not needed for DDL generation):
- IF EXISTS clause (pgdelta tracks existence, so always knows if view exists)
- CASCADE option (dependency resolution handles ordering, making CASCADE unnecessary)
- RESTRICT option (default PostgreSQL behavior, handled by dependency resolution)
- Dropping multiple views in one statement (handled by generating separate statements)

TODO: Views can create dependency cycles. For example:
- View A depends on View B
- View B depends on View A (through a recursive CTE or complex query)
When this occurs, PostgreSQL may require special handling or prevent the creation.
We should detect these cycles and provide appropriate error messages or handling.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class DropView:
    """Drop view change."""

    stable_id: str
    namespace: str
    relname: str


def generate_drop_view_sql(change: DropView) -> str:
    """Generate DROP VIEW SQL."""
    quoted_schema = f'"{change.namespace}"'
    quoted_view = f'"{change.relname}"'

    return f"DROP VIEW {quoted_schema}.{quoted_view};"
