"""Type diff operations."""

from pgdelta.catalog import PgCatalog
from pgdelta.changes.type import CreateType, DropType


def diff_types(master: PgCatalog, branch: PgCatalog) -> list[CreateType | DropType]:
    """Generate type changes between master and branch catalogs."""
    changes: list[CreateType | DropType] = []

    # Find types to drop (in master but not in branch)
    for stable_id, master_type in master.types.items():
        if stable_id not in branch.types:
            drop_change = DropType(
                stable_id=stable_id,
                namespace=master_type.namespace,
                typname=master_type.typname,
            )
            changes.append(drop_change)

    # Find types to create (in branch but not in master)
    for stable_id, branch_type in branch.types.items():
        if stable_id not in master.types:
            create_change = CreateType(
                stable_id=stable_id,
                namespace=branch_type.namespace,
                typname=branch_type.typname,
                typtype=branch_type.typtype,
                enum_values=branch_type.enum_values,
                domain_base_type=branch_type.domain_base_type,
                domain_constraints=branch_type.domain_constraints,
                composite_attributes=branch_type.composite_attributes,
                range_subtype=branch_type.range_subtype,
                multirange_range_type=branch_type.multirange_range_type,
            )
            changes.append(create_change)

    # Handle type modifications by checking for semantic differences
    # If types differ, we use DROP + CREATE approach (safer than ALTER TYPE)
    for stable_id, branch_type in branch.types.items():
        if stable_id in master.types:
            master_type = master.types[stable_id]

            # Check if types are semantically different
            if not master_type.semantic_equality(branch_type):
                # Drop the old type and create the new one
                drop_change = DropType(
                    stable_id=stable_id,
                    namespace=master_type.namespace,
                    typname=master_type.typname,
                )
                changes.append(drop_change)

                create_change = CreateType(
                    stable_id=stable_id,
                    namespace=branch_type.namespace,
                    typname=branch_type.typname,
                    typtype=branch_type.typtype,
                    enum_values=branch_type.enum_values,
                    domain_base_type=branch_type.domain_base_type,
                    domain_constraints=branch_type.domain_constraints,
                    composite_attributes=branch_type.composite_attributes,
                    range_subtype=branch_type.range_subtype,
                    multirange_range_type=branch_type.multirange_range_type,
                )
                changes.append(create_change)

    return changes
