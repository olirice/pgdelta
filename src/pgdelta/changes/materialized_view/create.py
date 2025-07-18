"""Create materialized view change type and SQL generation.

PostgreSQL 17 CREATE MATERIALIZED VIEW Synopsis:
https://www.postgresql.org/docs/17/sql-creatematerializedview.html

CREATE MATERIALIZED VIEW [ IF NOT EXISTS ] table_name
    [ (column_name [, ...]) ]
    [ USING method ]
    [ WITH ( storage_parameter [= value] [, ...] ) ]
    [ TABLESPACE tablespace_name ]
    AS query
    [ WITH [ NO ] DATA ]

Implementation Notes:
This implementation uses pg_get_viewdef() to extract the complete view definition
directly from PostgreSQL's system catalogs. This approach automatically supports ALL
PostgreSQL materialized view features without manual implementation.

We always create materialized views with NO DATA to avoid potential data issues
during schema migrations. The view can be refreshed after creation if needed.

Currently supported (via pg_get_viewdef):
- All SELECT query features
- Column name specification
- Complex queries with JOINs, CTEs, etc.

Not yet supported:
- Storage parameters (WITH clause)
- USING method specification

Intentionally not supported:
- WITH DATA option (we always use NO DATA for safety)
- Tablespace specification
- IF NOT EXISTS option (pgdelta tracks existence)
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class CreateMaterializedView:
    """Create materialized view change (CREATE MATERIALIZED VIEW)."""

    stable_id: str
    namespace: str
    relname: str
    definition: str


def generate_create_materialized_view_sql(change: CreateMaterializedView) -> str:
    """Generate CREATE MATERIALIZED VIEW SQL using pg_get_viewdef.

    Note: We always create materialized views with NO DATA to avoid potential
    data consistency issues during schema migrations. The view can be refreshed
    after creation if needed.
    """
    quoted_schema = f'"{change.namespace}"'
    quoted_name = f'"{change.relname}"'

    # Use the view definition from pg_get_viewdef()
    # This ensures we get the exact SQL that PostgreSQL would use
    # Note: pg_get_viewdef() returns just the SELECT query, not the full DDL
    definition = change.definition.strip()

    # Remove any trailing semicolon from the definition - pg_get_viewdef sometimes includes it
    if definition.endswith(";"):
        definition = definition[:-1]

    # Construct the full CREATE MATERIALIZED VIEW statement
    # The WITH NO DATA clause must come after the query
    sql = f"CREATE MATERIALIZED VIEW {quoted_schema}.{quoted_name} AS {definition} WITH NO DATA"

    return sql + ";"
