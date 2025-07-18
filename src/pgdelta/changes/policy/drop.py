"""Drop policy operations."""

from dataclasses import dataclass


@dataclass(frozen=True)
class DropPolicy:
    """Drop a row-level security policy."""

    stable_id: str
    namespace: str
    tablename: str
    polname: str


def generate_drop_policy_sql(change: DropPolicy) -> str:
    """Generate SQL for dropping an RLS policy."""
    quoted_schema = f'"{change.namespace}"'
    quoted_table = f'"{change.tablename}"'
    quoted_policy = f'"{change.polname}"'

    return f"DROP POLICY {quoted_policy} ON {quoted_schema}.{quoted_table};"
