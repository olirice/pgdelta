"""Replace function change type and SQL generation.

PostgreSQL 17 CREATE OR REPLACE FUNCTION Synopsis:
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
and converts them to CREATE OR REPLACE FUNCTION statements. This approach automatically
supports ALL PostgreSQL function features.

Fully Supported (via pg_get_functiondef):
- All function replacement scenarios using CREATE OR REPLACE FUNCTION
- Complete preservation of all function attributes and properties
- All PostgreSQL function features (see create.py for full list)

Note: PostgreSQL ALTER FUNCTION is limited in what it can change (only a few attributes
like volatility, security, and configuration). For most function changes (signature,
return type, body), we use CREATE OR REPLACE FUNCTION which is more flexible and the
standard approach in PostgreSQL.
"""

from dataclasses import dataclass

from ...model import PgProc


@dataclass(frozen=True)
class ReplaceFunction:
    """Replace function change (CREATE OR REPLACE FUNCTION)."""

    old_procedure: PgProc
    new_procedure: PgProc

    @property
    def stable_id(self) -> str:
        """Stable identifier for this change."""
        return self.new_procedure.stable_id


def generate_replace_function_sql(change: ReplaceFunction) -> str:
    """Generate CREATE OR REPLACE FUNCTION SQL using pg_get_functiondef.

    PostgreSQL doesn't allow ALTER FUNCTION to change most function properties.
    Instead, we use CREATE OR REPLACE FUNCTION which is the standard way
    to modify functions in PostgreSQL.
    """
    proc = change.new_procedure

    # Use the complete function definition and convert to CREATE OR REPLACE
    function_def = proc.function_definition.strip()

    # Replace "CREATE FUNCTION" with "CREATE OR REPLACE FUNCTION"
    sql = function_def.replace("CREATE FUNCTION", "CREATE OR REPLACE FUNCTION", 1)

    # Ensure the SQL ends with a semicolon
    if not sql.endswith(";"):
        sql += ";"

    return sql
