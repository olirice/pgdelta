"""Create function change type and SQL generation.

PostgreSQL 17 CREATE FUNCTION Synopsis:
https://www.postgresql.org/docs/17/sql-createfunction.html

CREATE [ OR REPLACE ] FUNCTION
    name ( [ [ argmode ] [ argname ] argtype [ { DEFAULT | = } default_expr ] [, ...] ] )
    [ RETURNS rettype
      | RETURNS TABLE ( column_name column_type [, ...] ) ]
  { LANGUAGE lang_name
    | TRANSFORM { FOR TYPE type_name } [, ... ]
    | WINDOW
    | { IMMUTABLE | STABLE | VOLATILE }
    | [ NOT ] LEAKPROOF
    | { CALLED ON NULL INPUT | RETURNS NULL ON NULL INPUT | STRICT }
    | { [ EXTERNAL ] SECURITY INVOKER | [ EXTERNAL ] SECURITY DEFINER }
    | PARALLEL { UNSAFE | RESTRICTED | SAFE }
    | COST execution_cost
    | ROWS result_rows
    | SUPPORT support_function
    | SET configuration_parameter { TO value | = value | FROM CURRENT }
    | AS 'definition'
    | AS 'obj_file', 'link_symbol'
    | sql_body
  } ...

Implementation Notes:
This implementation uses pg_get_functiondef() to extract complete function definitions
directly from PostgreSQL's system catalogs. This approach automatically supports ALL
PostgreSQL function features without manual implementation, including:

Fully Supported (via pg_get_functiondef):
- All argument modes (IN, OUT, INOUT, VARIADIC)
- Argument names and default values
- All return types including RETURNS TABLE
- All function languages (SQL, PL/pgSQL, C, etc.)
- WINDOW functions
- Volatility (IMMUTABLE, STABLE, VOLATILE)
- Security context (SECURITY DEFINER/INVOKER)
- Strictness (STRICT, CALLED ON NULL INPUT, RETURNS NULL ON NULL INPUT)
- Parallel safety (PARALLEL UNSAFE/RESTRICTED/SAFE)
- Cost and rows estimation
- Configuration parameters (SET parameter = value)
- Support functions
- Transform specifications
- All function body formats (AS 'definition', AS $$body$$, sql_body)

Intentionally Not Supported:
- External functions (AS 'obj_file', 'link_symbol') - these require file system access
"""

from dataclasses import dataclass

from ...model import PgProc


@dataclass(frozen=True)
class CreateFunction:
    """Create function change (CREATE FUNCTION)."""

    procedure: PgProc

    @property
    def stable_id(self) -> str:
        """Stable identifier for this change."""
        return self.procedure.stable_id


def generate_create_function_sql(change: CreateFunction) -> str:
    """Generate CREATE FUNCTION SQL using pg_get_functiondef."""
    proc = change.procedure

    # Use the complete function definition extracted from PostgreSQL
    # pg_get_functiondef() provides the exact DDL that PostgreSQL would use
    sql = proc.function_definition.strip()

    # Ensure the SQL ends with a semicolon
    if not sql.endswith(";"):
        sql += ";"

    return sql
