"""Drop function change type and SQL generation.

PostgreSQL 17 DROP FUNCTION Synopsis:
https://www.postgresql.org/docs/17/sql-dropfunction.html

DROP FUNCTION [ IF EXISTS ] name [ ( [ [ argmode ] [ argname ] argtype [, ...] ] ) ] [, ...]
    [ CASCADE | RESTRICT ]

Currently supported:
- Basic function dropping with schema-qualified names
- Argument type specification for function overloads

Intentionally Not Supported:
- IF EXISTS option
- CASCADE
"""

from dataclasses import dataclass

from ...model import PgProc


@dataclass(frozen=True)
class DropFunction:
    """Drop function change (DROP FUNCTION)."""

    procedure: PgProc

    @property
    def stable_id(self) -> str:
        """Stable identifier for this change."""
        return self.procedure.stable_id


def generate_drop_function_sql(change: DropFunction) -> str:
    """Generate DROP FUNCTION SQL."""
    proc = change.procedure

    # Format function signature for dropping
    quoted_schema = f'"{proc.namespace}"'
    quoted_name = f'"{proc.proname}"'

    # Include argument types to handle function overloads
    args = proc.proargtypes if proc.proargtypes else ""

    # Dependency resolution handles ordering, no CASCADE needed
    sql = f"DROP FUNCTION {quoted_schema}.{quoted_name}({args})"

    return sql + ";"
