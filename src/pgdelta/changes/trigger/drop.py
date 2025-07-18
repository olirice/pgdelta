"""Drop trigger change type and SQL generation.

PostgreSQL 17 DROP TRIGGER Synopsis:
https://www.postgresql.org/docs/17/sql-droptrigger.html

DROP TRIGGER [ IF EXISTS ] name ON table_name [ CASCADE | RESTRICT ]

Currently supported:
- Basic trigger dropping with table-qualified names

Intentionally Not Supported:
- IF EXISTS option
- CASCADE - pgdelta uses dependency resolution instead of CASCADE
- RESTRICT option (default behavior)
"""

from dataclasses import dataclass

from ...model import PgTrigger


@dataclass(frozen=True)
class DropTrigger:
    """Drop trigger change (DROP TRIGGER)."""

    trigger: PgTrigger

    @property
    def stable_id(self) -> str:
        """Stable identifier for this change."""
        return self.trigger.stable_id


def generate_drop_trigger_sql(change: DropTrigger) -> str:
    """Generate DROP TRIGGER SQL."""
    trigger = change.trigger

    # Format trigger drop statement with table qualification
    quoted_schema = f'"{trigger.namespace}"'
    quoted_table = f'"{trigger.table_name}"'
    quoted_trigger = f'"{trigger.tgname}"'

    # Dependency resolution handles ordering, no CASCADE needed
    sql = f"DROP TRIGGER {quoted_trigger} ON {quoted_schema}.{quoted_table}"

    return sql + ";"
