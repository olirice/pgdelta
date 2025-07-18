"""PostgreSQL trigger model."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy import text

from .base import BasePgModel, field_data, field_identity, field_internal

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


@dataclass(slots=True, frozen=True)
class PgTrigger(BasePgModel):
    """PostgreSQL trigger model."""

    # Identity fields (no defaults)
    tgname: str = field_identity()
    namespace: str = field_identity()  # Computed from table join
    table_name: str = field_identity()  # Name of the table the trigger is on

    # Data fields (no defaults)
    trigger_definition: str = field_data()  # Complete DDL from pg_get_triggerdef()

    # Internal fields (no defaults) - needed for dependency resolution
    oid: int = field_internal()
    tgrelid: int = field_internal()  # OID of the table the trigger is on
    tgfoid: int = field_internal()  # OID of the function called by the trigger

    @property
    def stable_id(self) -> str:
        """
        Database-portable stable identifier for dependency resolution.
        Format: "trigger:namespace.table_name.trigger_name"
        (e.g., "trigger:public.users.update_timestamp")
        """
        return f"trigger:{self.namespace}.{self.table_name}.{self.tgname}"

    @property
    def qualified_name(self) -> str:
        """Fully qualified trigger name including table."""
        return f"{self.namespace}.{self.table_name}.{self.tgname}"

    @property
    def function_stable_id(self) -> str:
        """Stable ID of the function this trigger calls (for dependency resolution)."""
        # Note: This is a simplified version. In a full implementation, we'd need to
        # resolve the function OID to its actual namespace.name(args) signature
        # For now, we'll compute this during extraction
        return f"function_oid:{self.tgfoid}"


def extract_triggers(session: "Session") -> list[PgTrigger]:
    """Extract triggers from pg_trigger."""
    # Set empty search_path to ensure fully qualified names
    session.execute(text("SET search_path = ''"))

    query = text(
        """
        SELECT
            t.oid,
            t.tgname,
            t.tgrelid,
            t.tgfoid,
            n.nspname as namespace,
            c.relname as table_name,
            -- Complete trigger definition DDL
            pg_catalog.pg_get_triggerdef(t.oid) as trigger_definition
        FROM pg_catalog.pg_trigger t
        JOIN pg_catalog.pg_class c ON t.tgrelid = c.oid
        JOIN pg_catalog.pg_namespace n ON c.relnamespace = n.oid
        WHERE n.nspname NOT IN ('information_schema', 'pg_catalog', 'pg_toast')
        AND n.nspname NOT LIKE 'pg_temp_%'
        AND n.nspname NOT LIKE 'pg_toast_temp_%'
        -- Exclude system triggers (constraint triggers are internal)
        AND NOT t.tgisinternal
        ORDER BY n.nspname, c.relname, t.tgname
    """
    )

    result = session.execute(query)
    triggers = []

    for row in result:
        trigger = PgTrigger(
            tgname=row.tgname,
            namespace=row.namespace,
            table_name=row.table_name,
            trigger_definition=row.trigger_definition,
            oid=row.oid,
            tgrelid=row.tgrelid,
            tgfoid=row.tgfoid,
        )
        triggers.append(trigger)

    return triggers
