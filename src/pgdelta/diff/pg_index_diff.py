"""Index diffing logic."""

from ..catalog import PgCatalog
from ..changes.dispatcher import DDL
from ..changes.index import AlterIndex, CreateIndex, DropIndex
from ..model.pg_index import PgIndex


def diff_indexes(master: PgCatalog, branch: PgCatalog) -> list[DDL]:
    """Generate index changes to transform master catalog to branch catalog."""
    changes: list[DDL] = []

    # Find indexes to drop (exist in master but not in branch)
    for stable_id, index in master.indexes.items():
        if stable_id not in branch.indexes and not index.is_constraint_index:
            # Skip constraint-created indexes - they're automatically dropped with constraints
            changes.append(
                DropIndex(
                    stable_id=stable_id,
                    index=index,
                )
            )

    # Find indexes to create (exist in branch but not in master)
    for stable_id, index in branch.indexes.items():
        if stable_id not in master.indexes and not index.is_constraint_index:
            # Skip constraint-created indexes - they're automatically created by constraints
            changes.append(
                CreateIndex(
                    stable_id=stable_id,
                    index=index,
                )
            )

    # Handle index modifications (same name, different definition)
    for stable_id, master_index in master.indexes.items():
        if stable_id in branch.indexes:
            branch_index = branch.indexes[stable_id]

            # Check if indexes are semantically different
            if not master_index.semantic_equality(branch_index):
                # For indexes, only name changes can be altered directly
                # All other changes require DROP + CREATE
                if _only_name_changed(master_index, branch_index):
                    changes.append(
                        AlterIndex(
                            stable_id=stable_id,
                            old_index=master_index,
                            new_index=branch_index,
                        )
                    )
                else:
                    # For structural changes, use drop + create
                    # Skip constraint-created indexes - they're managed by constraints
                    if (
                        not master_index.is_constraint_index
                        and not branch_index.is_constraint_index
                    ):
                        changes.append(
                            DropIndex(
                                stable_id=stable_id,
                                index=master_index,
                            )
                        )
                        changes.append(
                            CreateIndex(
                                stable_id=stable_id,
                                index=branch_index,
                            )
                        )

    return changes


def _only_name_changed(old_index: PgIndex, new_index: PgIndex) -> bool:
    """Check if only the name changed between indexes."""
    # Everything else must be identical for a simple rename
    return (
        old_index.namespace_name == new_index.namespace_name
        and old_index.table_name == new_index.table_name
        and old_index.is_unique == new_index.is_unique
        and old_index.is_primary == new_index.is_primary
        and old_index.is_constraint_index == new_index.is_constraint_index
        and old_index.index_definition == new_index.index_definition
        and old_index.name != new_index.name  # Name must be different
    )
