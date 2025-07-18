"""Alter index change type and SQL generation.

PostgreSQL index operations:

ALTER INDEX:
ALTER INDEX [IF EXISTS] name SET TABLESPACE tablespace_name
ALTER INDEX [IF EXISTS] name DEPENDS ON EXTENSION extension_name
ALTER INDEX [IF EXISTS] name SET ( storage_parameter [= value] [, ... ] )
ALTER INDEX [IF EXISTS] name RESET ( storage_parameter [, ... ] )

Currently supported:

Not yet supported:
- SET/RESET storage parameters
- SET/RESET statistics targets

Intentionally not supported:
- ALTER INDEX RENAME TO (name changes are handled as DROP + CREATE)
- Most ALTER INDEX operations are rarely used in schema migrations
- Index recreation (DROP + CREATE) is often simpler and safer
- SET TABLESPACE (tablespace changes)
- DEPENDS ON EXTENSION (extension dependencies)
"""

from dataclasses import dataclass

from ...model.pg_index import PgIndex


@dataclass(frozen=True)
class AlterIndex:
    """Alter index change."""

    stable_id: str  # i:namespace.index_name
    old_index: PgIndex
    new_index: PgIndex
