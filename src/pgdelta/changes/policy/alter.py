"""ALTER POLICY change types and SQL generation.

PostgreSQL 17 ALTER POLICY Synopsis:
https://www.postgresql.org/docs/17/sql-alterpolicy.html

ALTER POLICY name ON table_name RENAME TO new_name

ALTER POLICY name ON table_name
    [ TO { role_name | PUBLIC | CURRENT_ROLE | CURRENT_USER | SESSION_USER } [, ...] ]
    [ USING ( using_expression ) ]
    [ WITH CHECK ( check_expression ) ]
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class RenamePolicyTo:
    """Rename policy to new name."""

    stable_id: str
    namespace: str
    tablename: str
    old_name: str
    new_name: str


@dataclass(frozen=True)
class AlterPolicy:
    """Alter policy roles, USING expression, or WITH CHECK expression."""

    stable_id: str
    namespace: str
    tablename: str
    policy_name: str
    new_roles: list[str] | None = None  # None means no change
    new_using: str | None = None  # None means no change, empty string means remove
    new_with_check: str | None = None  # None means no change, empty string means remove


def generate_rename_policy_sql(change: RenamePolicyTo) -> str:
    """Generate SQL for renaming a policy."""
    quoted_schema = f'"{change.namespace}"'
    quoted_table = f'"{change.tablename}"'
    quoted_old_name = f'"{change.old_name}"'
    quoted_new_name = f'"{change.new_name}"'

    return f"ALTER POLICY {quoted_old_name} ON {quoted_schema}.{quoted_table} RENAME TO {quoted_new_name};"


def generate_alter_policy_sql(change: AlterPolicy) -> str:
    """Generate SQL for altering a policy."""
    quoted_schema = f'"{change.namespace}"'
    quoted_table = f'"{change.tablename}"'
    quoted_policy = f'"{change.policy_name}"'

    sql_parts = [f"ALTER POLICY {quoted_policy} ON {quoted_schema}.{quoted_table}"]

    # Add TO clause if roles are being changed
    if change.new_roles is not None:
        if change.new_roles:
            roles_str = ", ".join(change.new_roles)
            sql_parts.append(f"TO {roles_str}")
        else:
            # Empty roles list - this is unusual but technically valid
            sql_parts.append("TO PUBLIC")  # Default fallback

    # Add USING clause if using expression is being changed
    if change.new_using is not None and change.new_using:
        sql_parts.append(f"USING ({change.new_using})")
        # Note: PostgreSQL doesn't support removing USING expression completely,
        # so empty string would be an error. Caller should validate this.

    # Add WITH CHECK clause if with check expression is being changed
    if change.new_with_check is not None and change.new_with_check:
        sql_parts.append(f"WITH CHECK ({change.new_with_check})")
        # Note: PostgreSQL doesn't support removing WITH CHECK expression completely,
        # so empty string would be an error. Caller should validate this.

    return " ".join(sql_parts) + ";"
