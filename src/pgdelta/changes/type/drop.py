"""DROP TYPE SQL generation."""

from dataclasses import dataclass


@dataclass(frozen=True)
class DropType:
    """DROP TYPE change."""

    stable_id: str
    namespace: str
    typname: str


def generate_drop_type_sql(change: DropType) -> str:
    """Generate DROP TYPE SQL statement."""
    quoted_schema = f'"{change.namespace}"'
    quoted_name = f'"{change.typname}"'
    qualified_name = f"{quoted_schema}.{quoted_name}"

    return f"DROP TYPE {qualified_name};"
