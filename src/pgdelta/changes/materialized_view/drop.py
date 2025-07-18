"""Drop materialized view change type and SQL generation.

PostgreSQL 17 DROP MATERIALIZED VIEW Synopsis:
https://www.postgresql.org/docs/17/sql-dropmaterializedview.html

DROP MATERIALIZED VIEW [ IF EXISTS ] name [, ...] [ CASCADE | RESTRICT ]

Currently supported:
- Basic materialized view dropping
- Proper schema and name quoting

Intentionally not supported:
- CASCADE/RESTRICT options (dependency resolution handles ordering)
- IF EXISTS option (pgdelta tracks existence)
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class DropMaterializedView:
    """Drop materialized view change (DROP MATERIALIZED VIEW)."""

    stable_id: str
    namespace: str
    relname: str


def generate_drop_materialized_view_sql(change: DropMaterializedView) -> str:
    """Generate DROP MATERIALIZED VIEW SQL."""
    quoted_schema = f'"{change.namespace}"'
    quoted_name = f'"{change.relname}"'

    return f"DROP MATERIALIZED VIEW {quoted_schema}.{quoted_name};"
