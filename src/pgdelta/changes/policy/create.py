"""Create policy operations.

PostgreSQL 17 CREATE POLICY Synopsis:
https://www.postgresql.org/docs/17/sql-createpolicy.html

CREATE POLICY name ON table_name
    [ AS { PERMISSIVE | RESTRICTIVE } ]
    [ FOR { ALL | SELECT | INSERT | UPDATE | DELETE } ]
    [ TO { role_name | PUBLIC | CURRENT_ROLE | CURRENT_USER | SESSION_USER } [, ...] ]
    [ USING ( using_expression ) ]
    [ WITH CHECK ( check_expression ) ]

Currently supported:
- Basic policy creation with name and table
- Command-specific policies (FOR clause)
- Role-based policies (TO clause)
- Row filtering with USING expressions
- New row validation with WITH CHECK expressions

Not yet supported:
- PERMISSIVE/RESTRICTIVE policy types
- Multiple role specifications

Intentionally not supported:
- None (all features are valid for DDL generation)
"""

from dataclasses import dataclass

from ...model import PgPolicy


@dataclass(frozen=True)
class CreatePolicy:
    """Create a row-level security policy."""

    stable_id: str
    policy: PgPolicy


def generate_create_policy_sql(change: CreatePolicy) -> str:
    """Generate SQL for creating an RLS policy."""
    policy = change.policy

    # Quote identifiers
    quoted_schema = f'"{policy.namespace}"'
    quoted_table = f'"{policy.tablename}"'
    quoted_policy = f'"{policy.polname}"'

    # Build the CREATE POLICY statement
    parts = [f"CREATE POLICY {quoted_policy} ON {quoted_schema}.{quoted_table}"]

    # Add AS clause (PERMISSIVE or RESTRICTIVE)
    if policy.polpermissive:
        parts.append("AS PERMISSIVE")
    else:
        parts.append("AS RESTRICTIVE")

    # Add FOR clause (command type)
    # Map PostgreSQL internal command codes to SQL keywords
    command_map = {
        "r": "SELECT",
        "a": "INSERT",
        "w": "UPDATE",
        "d": "DELETE",
        "*": "ALL",
    }

    if policy.polcmd != "*":  # "*" means ALL
        command_name = command_map.get(policy.polcmd, policy.polcmd)
        parts.append(f"FOR {command_name}")
    else:
        parts.append("FOR ALL")

    # Add TO clause (roles)
    if policy.polroles:
        if len(policy.polroles) == 1 and policy.polroles[0] == "public":
            parts.append("TO public")
        else:
            # Quote role names that need it
            quoted_roles = []
            for role in policy.polroles:
                if role in ("public", "current_user", "session_user"):
                    quoted_roles.append(role)
                else:
                    quoted_roles.append(f'"{role}"')
            parts.append(f"TO {', '.join(quoted_roles)}")

    # Add USING clause (for SELECT, UPDATE, DELETE, and ALL)
    if policy.polqual:
        parts.append(f"USING ({policy.polqual})")

    # Add WITH CHECK clause (for INSERT, UPDATE, and ALL)
    if policy.polwithcheck:
        parts.append(f"WITH CHECK ({policy.polwithcheck})")

    return " ".join(parts) + ";"
