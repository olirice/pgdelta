"""Create view change type and SQL generation.

PostgreSQL 17 CREATE VIEW Synopsis:
https://www.postgresql.org/docs/17/sql-createview.html

CREATE [ OR REPLACE ] [ TEMP | TEMPORARY ] [ RECURSIVE ] VIEW name [ ( column_name [, ...] ) ]
    [ WITH ( view_option_name [= view_option_value] [, ... ] ) ]
    AS query
    [ WITH [ CASCADED | LOCAL ] CHECK OPTION ]

Currently supported:
- Basic view creation with schema-qualified names
- View definition (AS query)

Not yet supported:
- Temporary views (TEMP | TEMPORARY)
- Recursive views (RECURSIVE)
- Explicit column names
- View options (WITH clause)
- Check option (WITH CHECK OPTION)
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class CreateView:
    """Create view change (CREATE VIEW)."""

    stable_id: str
    namespace: str
    relname: str
    definition: str  # The SQL query defining the view


def generate_create_view_sql(change: CreateView) -> str:
    """Generate CREATE VIEW SQL."""
    quoted_schema = f'"{change.namespace}"'
    quoted_view = f'"{change.relname}"'

    # Clean up the definition - remove trailing semicolon if present
    definition = change.definition.rstrip(";").strip()

    sql = f"CREATE VIEW {quoted_schema}.{quoted_view} AS {definition}"

    return sql + ";"
