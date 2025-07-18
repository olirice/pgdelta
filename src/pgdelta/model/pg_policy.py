"""PostgreSQL row-level security policy model."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy import text

from .base import BasePgModel, field_data, field_identity, field_internal

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


@dataclass(slots=True, frozen=True)
class PgPolicy(BasePgModel):
    """PostgreSQL row-level security policy model."""

    # Identity fields (no defaults)
    polname: str = field_identity()  # Policy name
    tablename: str = field_identity()  # Table name (computed from join)
    namespace: str = field_identity()  # Schema name (computed from join)

    # Data fields (no defaults)
    polcmd: str = field_data()  # Command type: ALL, SELECT, INSERT, UPDATE, DELETE
    polpermissive: bool = field_data()  # True for PERMISSIVE, False for RESTRICTIVE
    polroles: list[str] = field_data()  # List of role names (array field)
    polqual: str | None = field_data()  # USING expression (for SELECT/DELETE)
    polwithcheck: str | None = field_data()  # WITH CHECK expression (for INSERT/UPDATE)

    # Internal fields (no defaults) - needed for dependency resolution
    oid: int = field_internal()

    @property
    def stable_id(self) -> str:
        """
        Database-portable stable identifier for dependency resolution.
        Format: "P:namespace.tablename.policyname" (e.g., "P:public.users.user_isolation")
        """
        return f"P:{self.namespace}.{self.tablename}.{self.polname}"

    @property
    def table_stable_id(self) -> str:
        """Get stable_id of the table this policy is attached to."""
        return f"r:{self.namespace}.{self.tablename}"


def extract_policies(session: "Session") -> list[PgPolicy]:
    """Extract RLS policies from pg_policy joined with pg_class and pg_namespace."""
    query = text(
        """
        SELECT
            pol.oid,
            pol.polname,
            c.relname as tablename,
            n.nspname as namespace,
            pol.polcmd,
            pol.polpermissive,
            CASE
                WHEN pol.polroles = '{0}' THEN ARRAY['public']::text[]
                ELSE ARRAY(
                    SELECT rolname
                    FROM pg_catalog.pg_roles
                    WHERE oid = ANY(pol.polroles)
                    ORDER BY rolname
                )
            END as polroles,
            pg_catalog.pg_get_expr(pol.polqual, c.oid) as polqual,
            pg_catalog.pg_get_expr(pol.polwithcheck, c.oid) as polwithcheck
        FROM pg_catalog.pg_policy pol
        JOIN pg_catalog.pg_class c ON pol.polrelid = c.oid
        JOIN pg_catalog.pg_namespace n ON c.relnamespace = n.oid
        WHERE n.nspname NOT IN ('information_schema', 'pg_catalog', 'pg_toast')
        AND n.nspname NOT LIKE 'pg_temp_%'
        AND n.nspname NOT LIKE 'pg_toast_temp_%'
        ORDER BY n.nspname, c.relname, pol.polname
    """
    )

    result = session.execute(query)
    policies = []

    for row in result:
        # Convert polroles array to list of strings
        polroles = list(row.polroles) if row.polroles else []

        pg_policy = PgPolicy(
            polname=row.polname,
            tablename=row.tablename,
            namespace=row.namespace,
            polcmd=row.polcmd,
            polpermissive=row.polpermissive,
            polroles=polroles,
            polqual=row.polqual,
            polwithcheck=row.polwithcheck,
            oid=row.oid,
        )
        policies.append(pg_policy)

    return policies
