"""PostgreSQL procedure (function) model."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy import text

from .base import BasePgModel, field_data, field_identity, field_internal

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


@dataclass(slots=True, frozen=True)
class PgProc(BasePgModel):
    """PostgreSQL procedure (function) model."""

    # Identity fields (no defaults)
    proname: str = field_identity()
    namespace: str = field_identity()  # Computed from join
    proargtypes: str = field_identity()  # Argument types as formatted string

    # Data fields (no defaults)
    function_definition: str = field_data()  # Complete DDL from pg_get_functiondef()

    # Internal fields (no defaults) - needed for dependency resolution
    oid: int = field_internal()
    proowner: int = field_internal()  # Owner's OID
    pronamespace: int = field_internal()  # Namespace OID

    @property
    def stable_id(self) -> str:
        """
        Database-portable stable identifier for dependency resolution.
        Format: "function:namespace.name(argtypes)" (e.g., "function:public.my_func(integer,text)")

        Including argument types ensures function overloads are treated as distinct objects.
        """
        return f"function:{self.namespace}.{self.proname}({self.proargtypes})"

    @property
    def signature(self) -> str:
        """Human-readable function signature."""
        args = self.proargtypes if self.proargtypes else ""
        return f"{self.proname}({args})"

    @property
    def qualified_name(self) -> str:
        """Fully qualified function name."""
        return f"{self.namespace}.{self.proname}"


def extract_procedures(session: "Session") -> list[PgProc]:
    """Extract procedures/functions from pg_proc."""
    # Set empty search_path to ensure fully qualified names
    session.execute(text("SET search_path = ''"))

    query = text(
        """
        SELECT
            p.oid,
            p.proname,
            p.pronamespace,
            p.proowner,
            n.nspname as namespace,
            -- Format argument types as comma-separated string
            pg_catalog.pg_get_function_identity_arguments(p.oid) as proargtypes,
            -- Complete function definition DDL
            pg_catalog.pg_get_functiondef(p.oid) as function_definition
        FROM pg_catalog.pg_proc p
        JOIN pg_catalog.pg_namespace n ON p.pronamespace = n.oid
        WHERE n.nspname NOT IN ('information_schema', 'pg_catalog', 'pg_toast')
        AND n.nspname NOT LIKE 'pg_temp_%'
        AND n.nspname NOT LIKE 'pg_toast_temp_%'
        AND p.prokind = 'f'  -- Only functions, not procedures or aggregates
        AND NOT EXISTS (
            SELECT 1 FROM pg_catalog.pg_depend d
            WHERE d.classid = 1255  -- pg_proc
            AND d.objid = p.oid
            AND d.deptype = 'i'  -- internal dependency (auto-generated)
        )
        ORDER BY n.nspname, p.proname, p.oid
    """
    )

    result = session.execute(query)
    procedures = []

    for row in result:
        proc = PgProc(
            proname=row.proname,
            namespace=row.namespace,
            proargtypes=row.proargtypes or "",
            function_definition=row.function_definition,
            oid=row.oid,
            proowner=row.proowner,
            pronamespace=row.pronamespace,
        )
        procedures.append(proc)

    return procedures
