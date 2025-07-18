"""Create index change type and SQL generation.

PostgreSQL 17 CREATE INDEX Synopsis:
https://www.postgresql.org/docs/17/sql-createindex.html

CREATE [ UNIQUE ] INDEX [ CONCURRENTLY ] [ [ IF NOT EXISTS ] name ]
ON [ ONLY ] table_name [ USING method ]
(
    { column_name | ( expression ) }
    [ COLLATE collation ]
    [ opclass [ ( opclass_parameter = value [, ...] ) ] ]
    [ ASC | DESC ]
    [ NULLS { FIRST | LAST } ]
    [, ...]
)
[ INCLUDE ( column_name [, ...] ) ]
[ NULLS [ NOT ] DISTINCT ]
[ WITH ( storage_parameter = value [, ...] ) ]
[ TABLESPACE tablespace_name ]
[ WHERE predicate ]

Currently supported:
- CREATE INDEX (regular indexes)
- CREATE UNIQUE INDEX (unique indexes)
- Partial indexes with WHERE clause
- Functional indexes with expressions
- All standard index methods (btree, hash, gin, gist, spgist, brin)
- Custom operator classes
- Collation specifications
- ASC/DESC ordering options
- NULLS FIRST/LAST options
- Expression indexes
- Multi-column indexes
- WITH storage parameters

Not yet supported:
- INCLUDE columns (covering indexes)
- NULLS [NOT] DISTINCT option
- ONLY modifier for inheritance
- TABLESPACE clause
- Operator class parameters

Intentionally not supported (not needed for DDL generation):
- CONCURRENTLY option (not needed for schema migration)
- IF NOT EXISTS (pgdelta tracks existence)
"""

from dataclasses import dataclass

from ...model.pg_index import PgIndex


@dataclass(frozen=True)
class CreateIndex:
    """Create index change."""

    stable_id: str  # i:namespace.index_name
    index: PgIndex


def generate_create_index_sql(change: CreateIndex) -> str:
    """Generate CREATE INDEX SQL from the stored index definition."""
    # PostgreSQL's pg_get_indexdef() returns the complete CREATE INDEX statement
    index_def = change.index.index_definition

    # Ensure it ends with a semicolon for consistency with other DDL statements
    if not index_def.endswith(";"):
        index_def += ";"

    return index_def
