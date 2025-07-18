"""Constraint diffing logic."""

from ..catalog import PgCatalog
from ..changes.constraint import AlterConstraint, CreateConstraint, DropConstraint
from ..changes.dispatcher import DDL
from ..model.pg_constraint import PgConstraint


def diff_constraints(master: PgCatalog, branch: PgCatalog) -> list[DDL]:
    """Generate constraint changes to transform master catalog to branch catalog."""
    changes: list[DDL] = []

    # Find constraints to drop (exist in master but not in branch)
    for stable_id, constraint in master.constraints.items():
        if stable_id not in branch.constraints:
            # Get table columns for the constraint's table
            table_columns = master.get_class_attributes(constraint.table_stable_id)

            # Get referenced table columns for foreign keys
            referenced_table_columns = None
            if constraint.contype == "f" and constraint.confrelid != 0:
                # Find the referenced table in the source catalog
                for class_stable_id, cls in master.classes.items():
                    if cls.oid == constraint.confrelid:
                        referenced_table_columns = master.get_class_attributes(
                            class_stable_id
                        )
                        break

            changes.append(
                DropConstraint(
                    stable_id=stable_id,
                    constraint=constraint,
                    table_columns=table_columns,
                    referenced_table_columns=referenced_table_columns,
                )
            )

    # Find constraints to create (exist in branch but not in master)
    for stable_id, constraint in branch.constraints.items():
        if stable_id not in master.constraints:
            # Get table columns for the constraint's table
            table_columns = branch.get_class_attributes(constraint.table_stable_id)

            # Get referenced table columns for foreign keys
            referenced_table_columns = None
            if constraint.contype == "f" and constraint.confrelid != 0:
                # Find the referenced table in the target catalog
                for class_stable_id, cls in branch.classes.items():
                    if cls.oid == constraint.confrelid:
                        referenced_table_columns = branch.get_class_attributes(
                            class_stable_id
                        )
                        break

            changes.append(
                CreateConstraint(
                    stable_id=stable_id,
                    constraint=constraint,
                    table_columns=table_columns,
                    referenced_table_columns=referenced_table_columns,
                )
            )

    # Handle constraint modifications (same name, different definition)
    for stable_id, master_constraint in master.constraints.items():
        if stable_id in branch.constraints:
            branch_constraint = branch.constraints[stable_id]

            # Check if constraints are semantically different
            if not master_constraint.semantic_equality(branch_constraint):
                # Get table columns for both constraints
                table_columns = branch.get_class_attributes(
                    branch_constraint.table_stable_id
                )

                # Get referenced table columns for foreign keys
                referenced_table_columns = None
                if (
                    branch_constraint.contype == "f"
                    and branch_constraint.confrelid != 0
                ):
                    for class_stable_id, cls in branch.classes.items():
                        if cls.oid == branch_constraint.confrelid:
                            referenced_table_columns = branch.get_class_attributes(
                                class_stable_id
                            )
                            break

                # For foreign key constraints with only deferrability changes, use AlterConstraint
                if branch_constraint.contype == "f" and _only_deferrability_changed(
                    master_constraint, branch_constraint
                ):
                    changes.append(
                        AlterConstraint(
                            stable_id=stable_id,
                            old_constraint=master_constraint,
                            new_constraint=branch_constraint,
                            table_columns=table_columns,
                            referenced_table_columns=referenced_table_columns,
                        )
                    )
                else:
                    # For other constraint types or structural changes, use drop + create
                    master_table_columns = master.get_class_attributes(
                        master_constraint.table_stable_id
                    )
                    master_referenced_table_columns = None
                    if (
                        master_constraint.contype == "f"
                        and master_constraint.confrelid != 0
                    ):
                        for class_stable_id, cls in master.classes.items():
                            if cls.oid == master_constraint.confrelid:
                                master_referenced_table_columns = (
                                    master.get_class_attributes(class_stable_id)
                                )
                                break

                    changes.append(
                        DropConstraint(
                            stable_id=stable_id,
                            constraint=master_constraint,
                            table_columns=master_table_columns,
                            referenced_table_columns=master_referenced_table_columns,
                        )
                    )
                    changes.append(
                        CreateConstraint(
                            stable_id=stable_id,
                            constraint=branch_constraint,
                            table_columns=table_columns,
                            referenced_table_columns=referenced_table_columns,
                        )
                    )

    return changes


def _only_deferrability_changed(
    old_constraint: PgConstraint, new_constraint: PgConstraint
) -> bool:
    """Check if only deferrability properties changed between constraints."""
    # For foreign key constraints, check if only deferrability properties differ
    return (
        old_constraint.contype == new_constraint.contype
        and old_constraint.conkey == new_constraint.conkey
        and old_constraint.confkey == new_constraint.confkey
        and old_constraint.confrelid == new_constraint.confrelid
        and old_constraint.confupdtype == new_constraint.confupdtype
        and old_constraint.confdeltype == new_constraint.confdeltype
        and old_constraint.confmatchtype == new_constraint.confmatchtype
        and old_constraint.conbin == new_constraint.conbin
        and old_constraint.conpredicate == new_constraint.conpredicate
        and
        # Only deferrability fields can differ
        (
            old_constraint.condeferrable != new_constraint.condeferrable
            or old_constraint.condeferred != new_constraint.condeferred
        )
    )
