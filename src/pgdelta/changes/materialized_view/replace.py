"""Replace materialized view change type and SQL generation.

PostgreSQL doesn't have CREATE OR REPLACE MATERIALIZED VIEW, so we need to
drop and recreate the materialized view when the definition changes.

This is implemented as a single change operation that generates the appropriate
DROP and CREATE statements in sequence.

Implementation Notes:
Unlike regular views, materialized views cannot use CREATE OR REPLACE.
The only way to modify a materialized view definition is to:
1. DROP MATERIALIZED VIEW (loses data)
2. CREATE MATERIALIZED VIEW WITH NO DATA (recreate structure)
3. REFRESH MATERIALIZED VIEW (repopulate data, if desired)

We always create with NO DATA to avoid potential data issues during migrations.
The materialized view can be refreshed after the migration if needed.

TODO:
- Materialized views with indexes will likely break the system

Currently supported:
- Complete materialized view recreation
- Preserves view name and schema
- Uses pg_get_viewdef() for accurate definition

Not yet supported:
- Storage parameter changes

Intentionally not supported:
- Incremental view modification (PostgreSQL limitation)
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ReplaceMaterializedView:
    """Replace materialized view change (DROP + CREATE MATERIALIZED VIEW)."""

    stable_id: str
    namespace: str
    relname: str
    definition: str


def generate_replace_materialized_view_sql(change: ReplaceMaterializedView) -> str:
    """Generate DROP + CREATE MATERIALIZED VIEW SQL.

    Since PostgreSQL doesn't support CREATE OR REPLACE MATERIALIZED VIEW,
    we drop and recreate the view. This loses any data in the materialized view.

    Note: We always create with NO DATA to avoid potential data consistency
    issues during schema migrations. The view can be refreshed after creation.
    """
    quoted_schema = f'"{change.namespace}"'
    quoted_name = f'"{change.relname}"'

    statements = []

    # Drop the existing materialized view
    statements.append(f"DROP MATERIALIZED VIEW {quoted_schema}.{quoted_name};")

    # Create the new materialized view with NO DATA
    # Handle potential semicolon in definition from pg_get_viewdef
    definition = change.definition.strip()
    if definition.endswith(";"):
        definition = definition[:-1]

    create_sql = f"CREATE MATERIALIZED VIEW {quoted_schema}.{quoted_name} AS {definition} WITH NO DATA;"
    statements.append(create_sql)

    return "\n".join(statements)
