"""PostgreSQL index model."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy import text

from .base import BasePgModel, field_data, field_identity, field_internal

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


@dataclass(slots=True, frozen=True)
class PgIndex(BasePgModel):
    """PostgreSQL index model."""

    # Identity fields
    name: str = field_identity()  # Index name (from pg_class.relname)
    namespace_name: str = field_identity()  # Schema name
    table_name: str = field_identity()  # Table the index belongs to

    # Data fields
    is_unique: bool = field_data()  # From pg_index.indisunique
    is_primary: bool = field_data()  # From pg_index.indisprimary
    is_constraint_index: bool = field_data()  # True if created by a constraint
    index_definition: str = field_data()  # From pg_get_indexdef()

    # Internal fields
    oid: int = field_internal()  # Index OID from pg_class
    table_oid: int = field_internal()  # Table OID from pg_index.indrelid

    @property
    def stable_id(self) -> str:
        """
        Database-portable stable identifier for dependency resolution.
        Format: "i:namespace.name" (e.g., "i:public.users_pkey")
        """
        return f"i:{self.namespace_name}.{self.name}"

    @property
    def table_stable_id(self) -> str:
        """Get the stable_id of the table this index belongs to."""
        return f"r:{self.namespace_name}.{self.table_name}"


def extract_indexes(session: "Session") -> list[PgIndex]:
    """Extract indexes from pg_class and pg_index."""
    # Set empty search_path to ensure fully qualified names in pg_get_indexdef()
    session.execute(text("SET search_path = ''"))

    query = text(
        """
        SELECT
            ci.oid,
            ci.relname as index_name,
            n.nspname as namespace_name,
            ct.relname as table_name,
            i.indrelid as table_oid,
            i.indisunique,
            i.indisprimary,
            pg_get_indexdef(i.indexrelid) as index_definition,
            -- Check if this index was created by a constraint
            CASE
                WHEN EXISTS (
                    SELECT 1 FROM pg_constraint c
                    WHERE c.conindid = i.indexrelid
                ) THEN true
                ELSE false
            END as is_constraint_index
        FROM pg_index i
        JOIN pg_class ci ON i.indexrelid = ci.oid
        JOIN pg_class ct ON i.indrelid = ct.oid
        JOIN pg_namespace n ON ci.relnamespace = n.oid
        WHERE n.nspname NOT IN ('information_schema', 'pg_catalog', 'pg_toast')
        AND n.nspname NOT LIKE 'pg_temp_%'
        AND n.nspname NOT LIKE 'pg_toast_temp_%'
        ORDER BY n.nspname, ci.relname
        """
    )

    result = session.execute(query)
    indexes = []

    for row in result:
        pg_index = PgIndex(
            name=row.index_name,
            namespace_name=row.namespace_name,
            table_name=row.table_name,
            is_unique=row.indisunique,
            is_primary=row.indisprimary,
            is_constraint_index=row.is_constraint_index,
            index_definition=row.index_definition,
            oid=row.oid,
            table_oid=row.table_oid,
        )
        indexes.append(pg_index)

    return indexes
