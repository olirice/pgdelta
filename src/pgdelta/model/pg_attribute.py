"""PostgreSQL attribute (column) model."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy import text

from .base import BasePgModel, field_data, field_identity, field_internal

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


@dataclass(slots=True, frozen=True)
class PgAttribute(BasePgModel):
    """PostgreSQL attribute (column) model."""

    # Owner information fields (grouped at top)
    owner_namespace: str = field_identity()  # Namespace of owning class
    owner_name: str = field_identity()  # Name of owning class
    owner_relkind: str = field_internal()  # Owner's relkind

    # Identity fields (no defaults)
    attname: str = field_identity()

    # Data fields (no defaults) - only fields needed for DDL generation
    attnum: int = field_data()  # Column position, needed for ordering
    attnotnull: bool = field_data()  # NOT NULL constraint
    formatted_type: str = field_data()  # Formatted type from format_type()

    # Internal fields (no defaults) - needed for dependency resolution
    attrelid: int = field_internal()

    # Fields with defaults (must come at the end)
    default_value: str | None = field_data(default=None)  # DEFAULT clause
    attgenerated: str = field_data(
        default=""
    )  # Generated column type: '' = not generated, 's' = stored
    generated_expression: str | None = field_data(
        default=None
    )  # Expression for generated column

    # TODO: Track function dependencies within generated column expressions
    # Generated columns can reference user-defined functions, and these dependencies
    # should be tracked for proper dependency resolution during schema migrations.
    # This would require parsing the generated_expression to identify function calls
    # and resolving them to pg_proc entries. Consider implementing this when adding
    # function/procedure support to pgdelta.

    @property
    def stable_id(self) -> str:
        """
        Database-portable stable identifier for dependency resolution.
        Format: "namespace.table.column" (e.g., "public.users.id")
        """
        return f"{self.owner_namespace}.{self.owner_name}.{self.attname}"

    @property
    def class_stable_id(self) -> str:
        """
        Stable identifier of the owning class (table/view/etc).
        Format: "relkind:namespace.name" (e.g., "r:public.users", "v:public.user_view")
        """
        return f"{self.owner_relkind}:{self.owner_namespace}.{self.owner_name}"

    @property
    def is_generated(self) -> bool:
        """Check if this column is a generated column."""
        # Future versions of postgres will likely add a non-stored verison
        return self.attgenerated == "s"

    @property
    def is_stored_generated(self) -> bool:
        """Check if this column is a stored generated column."""
        return self.attgenerated == "s"


def extract_attributes(session: "Session") -> list[PgAttribute]:
    """Extract attributes from pg_attribute."""
    # Set empty search_path to ensure fully qualified names in pg_get_expr() and format_type()
    session.execute(text("SET search_path = ''"))

    query = text(
        """
        SELECT
            a.attrelid,
            a.attname,
            a.attnum,
            a.attnotnull,
            n.nspname as owner_namespace,
            c.relname as owner_name,
            c.relkind as owner_relkind,
            pg_catalog.format_type(a.atttypid, a.atttypmod) as formatted_type,
            CASE
                WHEN a.attgenerated = '' THEN pg_catalog.pg_get_expr(d.adbin, d.adrelid)
                ELSE NULL
            END as default_value,
            COALESCE(a.attgenerated, '') as attgenerated,
            CASE
                WHEN a.attgenerated = 's' THEN pg_catalog.pg_get_expr(g.adbin, g.adrelid, true)
                ELSE NULL
            END as generated_expression
        FROM pg_catalog.pg_attribute a
        JOIN pg_catalog.pg_class c ON a.attrelid = c.oid
        JOIN pg_catalog.pg_namespace n ON c.relnamespace = n.oid
        LEFT JOIN pg_attrdef d ON a.attrelid = d.adrelid AND a.attnum = d.adnum AND a.attgenerated = ''
        LEFT JOIN pg_attrdef g ON a.attrelid = g.adrelid AND a.attnum = g.adnum AND a.attgenerated = 's'
        WHERE n.nspname NOT IN ('information_schema', 'pg_catalog', 'pg_toast')
        AND n.nspname NOT LIKE 'pg_temp_%'
        AND n.nspname NOT LIKE 'pg_toast_temp_%'
        AND a.attnum > 0
        AND NOT a.attisdropped
        ORDER BY n.nspname, c.relname, a.attnum
    """
    )

    result = session.execute(query)
    attributes = []

    for row in result:
        attribute = PgAttribute(
            owner_namespace=row.owner_namespace,
            owner_name=row.owner_name,
            owner_relkind=row.owner_relkind,
            attname=row.attname,
            attnum=row.attnum,
            attnotnull=row.attnotnull,
            formatted_type=row.formatted_type,
            attrelid=row.attrelid,
            default_value=row.default_value,
            attgenerated=row.attgenerated,
            generated_expression=row.generated_expression,
        )
        attributes.append(attribute)

    return attributes
