"""PostgreSQL namespace (schema) model."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy import text

from .base import BasePgModel, field_identity, field_internal

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


@dataclass(slots=True, frozen=True)
class PgNamespace(BasePgModel):
    """PostgreSQL namespace (schema) model."""

    # Identity fields (no defaults)
    nspname: str = field_identity()

    # Internal fields (no defaults) - needed for dependency resolution
    oid: int = field_internal()

    @property
    def stable_id(self) -> str:
        """
        Database-portable stable identifier for dependency resolution.
        Format: schema name (e.g., "public")
        """
        return self.nspname


def extract_namespaces(session: "Session") -> list[PgNamespace]:
    """Extract namespaces from pg_namespace."""
    query = text(
        """
        SELECT
            oid,
            nspname
        FROM pg_catalog.pg_namespace
        WHERE nspname NOT IN ('information_schema', 'pg_catalog', 'pg_toast')
        AND nspname NOT LIKE 'pg_temp_%'
        AND nspname NOT LIKE 'pg_toast_temp_%'
        ORDER BY nspname
    """
    )

    result = session.execute(query)
    namespaces = []

    for row in result:
        namespace = PgNamespace(
            nspname=row.nspname,
            oid=row.oid,
        )
        namespaces.append(namespace)

    return namespaces
