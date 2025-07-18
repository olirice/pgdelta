"""Create schema change type and SQL generation.

PostgreSQL 17 CREATE SCHEMA Synopsis:
https://www.postgresql.org/docs/17/sql-createschema.html

CREATE SCHEMA [ IF NOT EXISTS ] schema_name [ AUTHORIZATION role_specification ] [ schema_element [ ... ] ]
CREATE SCHEMA [ IF NOT EXISTS ] AUTHORIZATION role_specification [ schema_element [ ... ] ]

Currently supported:
- Basic schema creation with schema name

Not yet supported:
- IF NOT EXISTS option
- AUTHORIZATION clause
- Schema elements (CREATE TABLE, CREATE VIEW, etc. in schema definition)

Intentionally not supported:
- None currently
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class CreateSchema:
    """Create schema change."""

    stable_id: str
    nspname: str


def generate_create_schema_sql(change: CreateSchema) -> str:
    """Generate CREATE SCHEMA SQL."""
    quoted_schema = f'"{change.nspname}"'

    # Basic CREATE SCHEMA
    sql = f"CREATE SCHEMA {quoted_schema}"

    # TODO: Add AUTHORIZATION when we have user resolution
    # TODO: Add privileges when we implement them

    return sql + ";"
