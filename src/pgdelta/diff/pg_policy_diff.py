"""Policy diff logic for RLS policies."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..catalog import PgCatalog
from ..changes import DDL, AlterPolicy, CreatePolicy, DropPolicy, RenamePolicyTo

if TYPE_CHECKING:
    from ..model import PgPolicy


def diff_policies(master: PgCatalog, branch: PgCatalog) -> list[DDL]:
    """Diff RLS policies between catalogs."""
    changes: list[DDL] = []

    # Get all unique stable_ids to process
    all_policy_ids = set(master.policies.keys()) | set(branch.policies.keys())

    for policy_id in all_policy_ids:
        master_policy: PgPolicy | None = master.policies.get(policy_id)
        branch_policy: PgPolicy | None = branch.policies.get(policy_id)

        # Handle creation/deletion cases
        match (master_policy, branch_policy):
            case (None, branch_policy) if branch_policy is not None:
                # Policy created
                changes.append(
                    CreatePolicy(
                        stable_id=branch_policy.stable_id,
                        policy=branch_policy,
                    )
                )

            case (master_policy, None) if master_policy is not None:
                # Policy dropped
                changes.append(
                    DropPolicy(
                        stable_id=master_policy.stable_id,
                        namespace=master_policy.namespace,
                        tablename=master_policy.tablename,
                        polname=master_policy.polname,
                    )
                )

            case (master_policy, branch_policy) if (
                master_policy is not None and branch_policy is not None
            ):
                # Policy exists in both - check for changes
                if not master_policy.semantic_equality(branch_policy):
                    # Policy changed - try to use ALTER POLICY when possible
                    policy_changes = diff_single_policy(master_policy, branch_policy)
                    changes.extend(policy_changes)

            case (None, None):
                # Both are None - this shouldn't happen in normal operation
                # but it makes the type checker happy
                continue

    return changes


def diff_single_policy(master_policy: PgPolicy, branch_policy: PgPolicy) -> list[DDL]:
    """Compare two policies and generate appropriate ALTER POLICY or DROP+CREATE changes."""
    changes: list[DDL] = []

    # Check if this is a policy rename (same namespace, table, but different name)
    # Note: This is a special case and quite rare in practice, but PostgreSQL supports it
    if (
        master_policy.namespace == branch_policy.namespace
        and master_policy.tablename == branch_policy.tablename
        and master_policy.polname != branch_policy.polname
        and master_policy.get_data_fields() == branch_policy.get_data_fields()
    ):
        # This is just a rename - use ALTER POLICY RENAME TO
        changes.append(
            RenamePolicyTo(
                stable_id=branch_policy.stable_id,
                namespace=branch_policy.namespace,
                tablename=branch_policy.tablename,
                old_name=master_policy.polname,
                new_name=branch_policy.polname,
            )
        )
        return changes

    # Check if we can use ALTER POLICY for the changes
    # ALTER POLICY can change: roles (TO), USING expression, WITH CHECK expression
    # ALTER POLICY cannot change: command type (FOR), permissive/restrictive type

    # If command type or permissive/restrictive changed, we must use drop + create
    if (
        master_policy.polcmd != branch_policy.polcmd
        or master_policy.polpermissive != branch_policy.polpermissive
    ):
        # Cannot use ALTER POLICY - use drop + create
        changes.append(
            DropPolicy(
                stable_id=master_policy.stable_id,
                namespace=master_policy.namespace,
                tablename=master_policy.tablename,
                polname=master_policy.polname,
            )
        )
        changes.append(
            CreatePolicy(
                stable_id=branch_policy.stable_id,
                policy=branch_policy,
            )
        )
        return changes

    # We can use ALTER POLICY - determine what changed
    needs_alter = False
    new_roles = None
    new_using = None
    new_with_check = None

    if master_policy.polroles != branch_policy.polroles:
        needs_alter = True
        new_roles = branch_policy.polroles

    if master_policy.polqual != branch_policy.polqual:
        needs_alter = True
        new_using = branch_policy.polqual

    if master_policy.polwithcheck != branch_policy.polwithcheck:
        needs_alter = True
        new_with_check = branch_policy.polwithcheck

    if needs_alter:
        changes.append(
            AlterPolicy(
                stable_id=branch_policy.stable_id,
                namespace=branch_policy.namespace,
                tablename=branch_policy.tablename,
                policy_name=branch_policy.polname,
                new_roles=new_roles,
                new_using=new_using,
                new_with_check=new_with_check,
            )
        )

    return changes
