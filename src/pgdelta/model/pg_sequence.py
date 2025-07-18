"""PostgreSQL sequence model."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy import text

from .base import BasePgModel, field_data, field_identity, field_internal

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


@dataclass(slots=True, frozen=True)
class PgSequence(BasePgModel):
    """PostgreSQL sequence model."""

    # Identity fields (no defaults)
    seqname: str = field_identity()
    namespace: str = field_identity()  # Computed from join

    # Data fields (no defaults)
    data_type: str = field_data()
    increment_by: int = field_data()
    min_value: int | None = field_data()
    max_value: int | None = field_data()
    start_value: int = field_data()
    cache_size: int = field_data()
    cycle: bool = field_data()

    # Internal fields (no defaults) - needed for dependency resolution
    oid: int = field_internal()

    # Data fields with defaults
    owned_by_table: str | None = field_data(default=None)
    owned_by_column: str | None = field_data(default=None)

    @property
    def stable_id(self) -> str:
        """
        Database-portable stable identifier for dependency resolution.
        Format: "S:namespace.name" (e.g., "S:public.users_id_seq")
        """
        return f"S:{self.namespace}.{self.seqname}"

    @property
    def table_stable_id(self) -> str | None:
        """Get stable_id of the table this sequence is owned by, if any."""
        if self.owned_by_table and self.owned_by_column:
            return f"r:{self.namespace}.{self.owned_by_table}"
        return None


def extract_sequences(session: "Session") -> list[PgSequence]:
    """Extract sequences from pg_sequence joined with pg_class."""
    query = text(
        """
        SELECT
            c.oid,
            c.relname as seqname,
            n.nspname as namespace,
            s.seqtypid::regtype::text as data_type,
            s.seqincrement as increment_by,
            s.seqmin as min_value,
            s.seqmax as max_value,
            s.seqstart as start_value,
            s.seqcache as cache_size,
            s.seqcycle as cycle,
            -- Extract owned by information from pg_depend
            CASE
                WHEN dep.refobjid IS NOT NULL THEN ref_c.relname
                ELSE NULL
            END as owned_by_table,
            CASE
                WHEN dep.refobjid IS NOT NULL THEN ref_a.attname
                ELSE NULL
            END as owned_by_column
        FROM pg_catalog.pg_sequence s
        JOIN pg_catalog.pg_class c ON s.seqrelid = c.oid
        JOIN pg_catalog.pg_namespace n ON c.relnamespace = n.oid
        LEFT JOIN pg_catalog.pg_depend dep ON (
            dep.objid = c.oid
            AND dep.classid = 1259  -- pg_class
            AND dep.objsubid = 0
            AND dep.deptype = 'a'   -- auto dependency (OWNED BY)
        )
        LEFT JOIN pg_catalog.pg_class ref_c ON dep.refobjid = ref_c.oid
        LEFT JOIN pg_catalog.pg_attribute ref_a ON (
            dep.refobjid = ref_a.attrelid
            AND dep.refobjsubid = ref_a.attnum
        )
        WHERE n.nspname NOT IN ('information_schema', 'pg_catalog', 'pg_toast')
        AND n.nspname NOT LIKE 'pg_temp_%'
        AND n.nspname NOT LIKE 'pg_toast_temp_%'
        ORDER BY n.nspname, c.relname
    """
    )

    result = session.execute(query)
    sequences = []

    for row in result:
        pg_sequence = PgSequence(
            seqname=row.seqname,
            namespace=row.namespace,
            data_type=row.data_type,
            increment_by=row.increment_by,
            min_value=row.min_value,
            max_value=row.max_value,
            start_value=row.start_value,
            cache_size=row.cache_size,
            cycle=row.cycle,
            oid=row.oid,
            owned_by_table=row.owned_by_table,
            owned_by_column=row.owned_by_column,
        )
        sequences.append(pg_sequence)

    return sequences
