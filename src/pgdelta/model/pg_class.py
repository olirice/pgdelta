"""PostgreSQL class (relations) model."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy import text

from .base import BasePgModel, field_data, field_identity, field_internal

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


@dataclass(slots=True, frozen=True)
class PgClass(BasePgModel):
    """PostgreSQL class (relations) model."""

    # Identity fields (no defaults)
    relname: str = field_identity()
    namespace: str = field_identity()  # Computed from join

    # Data fields (no defaults)
    relkind: str = field_data()

    # Internal fields (no defaults) - needed for dependency resolution
    oid: int = field_internal()

    # Optional data fields (with defaults)
    view_definition: str | None = field_data(default=None)
    relrowsecurity: bool = field_data(default=False)  # RLS enabled on this table

    @property
    def stable_id(self) -> str:
        """
        Database-portable stable identifier for dependency resolution.
        Format: "relkind:namespace.name" (e.g., "r:public.users", "v:public.user_view")

        Including relkind ensures that tables, views, and materialized views with
        the same name are treated as distinct objects, simplifying diff logic.
        """
        return f"{self.relkind}:{self.namespace}.{self.relname}"


def extract_classes(session: "Session") -> list[PgClass]:
    """Extract classes from pg_class."""
    # Set empty search_path to ensure fully qualified names in pg_get_viewdef()
    session.execute(text("SET search_path = ''"))

    query = text(
        """
        SELECT
            c.oid,
            c.relname,
            c.relkind,
            n.nspname as namespace,
            CASE
                WHEN c.relkind IN ('v', 'm') THEN pg_catalog.pg_get_viewdef(c.oid)
                ELSE NULL
            END as view_definition,
            c.relrowsecurity
        FROM pg_catalog.pg_class c
        JOIN pg_catalog.pg_namespace n ON c.relnamespace = n.oid
        WHERE n.nspname NOT IN ('information_schema', 'pg_catalog', 'pg_toast')
        AND n.nspname NOT LIKE 'pg_temp_%'
        AND n.nspname NOT LIKE 'pg_toast_temp_%'
        AND c.relkind != 'S'  -- Exclude sequences (handled in sequences field)
        ORDER BY n.nspname, c.relname
    """
    )

    result = session.execute(query)
    classes = []

    for row in result:
        view_definition = row.view_definition.strip() if row.view_definition else None

        pg_class = PgClass(
            relname=row.relname,
            namespace=row.namespace,
            relkind=row.relkind,
            oid=row.oid,
            view_definition=view_definition,
            relrowsecurity=row.relrowsecurity,
        )
        classes.append(pg_class)

    return classes
