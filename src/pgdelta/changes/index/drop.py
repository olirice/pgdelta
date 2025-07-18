"""Drop index change type and SQL generation.

PostgreSQL index operations:

DROP INDEX:
DROP INDEX [CONCURRENTLY] [IF EXISTS] name [, ...] [CASCADE | RESTRICT]

Currently supported:
- DROP INDEX (regular drop)
- Schema-qualified index names
- CASCADE option when needed for dependencies

Not yet supported:
- CONCURRENTLY option (for online index removal)
- IF EXISTS option (pgdelta assumes index exists)
- Multiple indexes in single statement

Intentionally not supported:
- CONCURRENTLY option (pgdelta assumes non-production usage for safety)
- IF EXISTS option (pgdelta should know what exists)
"""

from dataclasses import dataclass

from ...model.pg_index import PgIndex


@dataclass(frozen=True)
class DropIndex:
    """Drop index change."""

    stable_id: str  # i:namespace.index_name
    index: PgIndex


def generate_drop_index_sql(change: DropIndex) -> str:
    """Generate DROP INDEX SQL."""
    index = change.index
    quoted_schema = f'"{index.namespace_name}"'
    quoted_name = f'"{index.name}"'

    return f"DROP INDEX {quoted_schema}.{quoted_name}"
