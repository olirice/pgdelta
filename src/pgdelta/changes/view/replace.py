"""Replace view change type and SQL generation.

PostgreSQL 17 CREATE OR REPLACE VIEW Synopsis:
https://www.postgresql.org/docs/17/sql-createview.html

CREATE [ OR REPLACE ] [ TEMP | TEMPORARY ] [ RECURSIVE ] VIEW name [ ( column_name [, ...] ) ]
    [ WITH ( view_option_name [= view_option_value] [, ... ] ) ]
    AS query
    [ WITH [ CASCADED | LOCAL ] CHECK OPTION ]

Currently supported:
- Basic view replacement with schema-qualified names
- View definition (AS query)

Not yet supported:
- Temporary views (TEMP | TEMPORARY)
- Recursive views (RECURSIVE)
- Explicit column names
- View options (WITH clause)
- Check option (WITH CHECK OPTION)

TODO: Current limitations and improvement opportunities:

1. CREATE OR REPLACE VIEW Structural Limitations:
   PostgreSQL's CREATE OR REPLACE VIEW has strict constraints on structural changes:
   - Cannot change column names (uses position-based matching)
   - Cannot reorder columns (column 1 must remain column 1)
   - Cannot change incompatible column types
   - Cannot add/remove columns in middle positions (can only append at end)

   When these limitations are violated, PostgreSQL will error with messages like:
   "cannot change name of view column 'old_name' to 'new_name'"
   "cannot change data type of view column 'col' from integer to text"

2. Alternative DDL Strategies Needed:
   - ALTER VIEW ALTER COLUMN for simple renames/type changes
   - DROP VIEW + CREATE VIEW for complex structural changes
   - Dependency cascade handling when views depend on the modified view

3. View Dependency Cycles:
   Views can reference each other in circular patterns:
   - View A: SELECT * FROM view_b WHERE condition
   - View B: SELECT * FROM view_a WHERE other_condition
   PostgreSQL prevents direct cycles but allows complex dependency chains.
   We should implement cycle detection in dependency resolution.

4. Error Handling Strategy:
   When CREATE OR REPLACE VIEW would fail due to structural changes and the view
   has dependencies, we should raise a descriptive exception explaining:
   - What structural change was attempted
   - Why CREATE OR REPLACE VIEW cannot handle it
   - Which objects depend on this view
   - Suggest manual intervention or staged migration approach

This aligns with pgdelta's philosophy of safe, explicit migrations rather than
attempting risky dependency cascades that could cause data loss.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ReplaceView:
    """Replace view change (CREATE OR REPLACE VIEW)."""

    stable_id: str
    namespace: str
    relname: str
    definition: str  # The SQL query defining the view


def generate_replace_view_sql(change: ReplaceView) -> str:
    """Generate CREATE OR REPLACE VIEW SQL."""
    quoted_schema = f'"{change.namespace}"'
    quoted_view = f'"{change.relname}"'

    # Clean up the definition - remove trailing semicolon if present
    definition = change.definition.rstrip(";").strip()

    sql = f"CREATE OR REPLACE VIEW {quoted_schema}.{quoted_view} AS {definition}"

    return sql + ";"
