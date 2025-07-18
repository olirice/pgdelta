"""Create trigger change type and SQL generation.

PostgreSQL 17 CREATE TRIGGER Synopsis:
https://www.postgresql.org/docs/17/sql-createtrigger.html

CREATE [ OR REPLACE ] [ CONSTRAINT ] TRIGGER name
{ BEFORE | AFTER | INSTEAD OF } { event [ OR ... ] }
ON table_name
[ FROM referenced_table_name ]
[ NOT DEFERRABLE | [ DEFERRABLE ] [ INITIALLY IMMEDIATE | INITIALLY DEFERRED ] ]
[ REFERENCING { { OLD | NEW } TABLE [ AS ] transition_relation_name } [ ... ] ]
[ FOR [ EACH ] { ROW | STATEMENT } ]
[ WHEN ( condition ) ]
EXECUTE { FUNCTION | PROCEDURE } function_name ( arguments )

Where event can be one of:
- INSERT
- UPDATE [ OF column_name [, ...] ]
- DELETE
- TRUNCATE

Implementation Notes:
This implementation uses pg_get_triggerdef() to extract complete trigger definitions
directly from PostgreSQL's system catalogs. This approach automatically supports ALL
PostgreSQL trigger features without manual implementation, including:

Fully Supported (via pg_get_triggerdef):
- All timing options (BEFORE, AFTER, INSTEAD OF)
- All event types (INSERT, UPDATE, DELETE, TRUNCATE)
- Column-specific UPDATE triggers
- Row-level and statement-level triggers
- WHEN conditions for conditional execution
- Constraint triggers with deferral options
- Transition relations (OLD/NEW TABLE AS)
- All trigger function calling conventions
- Multi-event triggers (INSERT OR UPDATE)

Intentionally Not Supported:
- OR REPLACE option (triggers must be dropped and recreated)
"""

from dataclasses import dataclass

from ...model import PgTrigger


@dataclass(frozen=True)
class CreateTrigger:
    """Create trigger change (CREATE TRIGGER)."""

    trigger: PgTrigger

    @property
    def stable_id(self) -> str:
        """Stable identifier for this change."""
        return self.trigger.stable_id


def generate_create_trigger_sql(change: CreateTrigger) -> str:
    """Generate CREATE TRIGGER SQL using pg_get_triggerdef."""
    trigger = change.trigger

    # Use the complete trigger definition extracted from PostgreSQL
    # pg_get_triggerdef() provides the exact DDL that PostgreSQL would use
    sql = trigger.trigger_definition.strip()

    # Ensure the SQL ends with a semicolon
    if not sql.endswith(";"):
        sql += ";"

    return sql
