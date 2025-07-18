"""Class diff logic for tables, views, etc."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..catalog import PgCatalog
from ..changes import DDL, CreateTable, CreateView, DropTable, DropView, ReplaceView
from ..changes.materialized_view import (
    CreateMaterializedView,
    DropMaterializedView,
    ReplaceMaterializedView,
)
from ..changes.table import (
    AddColumn,
    AlterColumnDropDefault,
    AlterColumnDropNotNull,
    AlterColumnSetDefault,
    AlterColumnSetNotNull,
    AlterColumnType,
    AlterTable,
    ColumnOperation,
    DisableRowLevelSecurity,
    DropColumn,
    EnableRowLevelSecurity,
)

if TYPE_CHECKING:
    from ..model import PgAttribute, PgClass


def diff_classes(master: PgCatalog, branch: PgCatalog) -> list[DDL]:
    """Diff classes (tables, views, etc.) between catalogs."""
    changes: list[DDL] = []

    # Get all unique stable_ids to process (now includes relkind)
    all_class_ids = set(master.classes.keys()) | set(branch.classes.keys())

    for class_id in all_class_ids:
        master_class: PgClass | None = master.classes.get(class_id)
        branch_class: PgClass | None = branch.classes.get(class_id)

        # Determine relkind from the actual class objects (source of truth)
        # we know at least 1 of these is non-None
        relkind = (master_class or branch_class).relkind  # type: ignore

        if relkind == "r":
            # Table operations
            changes.extend(
                diff_table_to_table(master, branch, master_class, branch_class)
            )
        elif relkind == "v":
            # View operations
            # TODO: Views can create dependency cycles. For example:
            # - View A depends on View B which depends on View A (recursive references)
            # - Complex view hierarchies that form circular dependencies
            # We should implement cycle detection in dependency resolution to handle this
            #
            # TODO: View DDL Strategy Tradeoffs
            # PostgreSQL has fundamental limitations with CREATE OR REPLACE VIEW that affect our DDL generation:
            #
            # CREATE OR REPLACE VIEW limitations:
            # - Cannot change column names (position-based matching)
            # - Cannot reorder columns (position 1 must stay position 1)
            # - Cannot change column types in incompatible ways
            # - Cannot add/remove columns in middle positions
            # - Can only append new columns at the end
            #
            # When CREATE OR REPLACE VIEW fails, we need alternative strategies:
            #
            # 1. ALTER VIEW ALTER COLUMN (limited cases):
            #    - Can rename columns: ALTER VIEW name RENAME COLUMN old TO new;
            #    - Can change column types: ALTER VIEW name ALTER COLUMN col TYPE new_type;
            #    - Cannot reorder columns or add/remove columns
            #
            # 2. DROP VIEW + CREATE VIEW (when dependencies allow):
            #    - Can handle any structural change
            #    - Requires dependency analysis: if other views/tables depend on this view,
            #      those dependencies must be dropped first, then recreated after
            #    - Dependency cascade can be expensive and risky
            #
            # 3. Exception for complex dependency cases:
            #    - If view has dependencies and requires DROP + CREATE (not just ALTER),
            #      raise a descriptive exception explaining:
            #      * What structural change was attempted (column reorder, type change, etc.)
            #      * Why CREATE OR REPLACE VIEW cannot handle it
            #      * Which objects depend on this view (list the dependent views/tables)
            #      * Suggest manual intervention or staged migration approach
            #
            # Implementation approach:
            # - First attempt CREATE OR REPLACE VIEW (current behavior)
            # - If that would fail due to structural changes, analyze dependencies
            # - If no dependencies: use DROP VIEW + CREATE VIEW
            # - If dependencies exist: raise detailed exception with guidance
            # - Consider adding ALTER VIEW ALTER COLUMN support for simple cases
            #
            # This aligns with pgdelta's philosophy of safe, explicit migrations rather than
            # attempting complex dependency cascades that could cause data loss.
            changes.extend(
                diff_view_to_view(master, branch, master_class, branch_class)
            )
        elif relkind == "m":
            # Materialized view operations
            changes.extend(
                diff_materialized_view_to_materialized_view(
                    master, branch, master_class, branch_class
                )
            )
        # Other relkinds (sequences, indexes, etc.) - skip for now

    return changes


def diff_table_to_table(
    master: PgCatalog,
    branch: PgCatalog,
    master_class: PgClass | None,
    branch_class: PgClass | None,
) -> list[DDL]:
    """Handle class-to-class diff operations (create, drop, modify)."""
    changes: list[DDL] = []

    # Handle creation/deletion cases
    match (master_class, branch_class):
        case (None, branch_class) if branch_class is not None:
            # Class created
            changes.append(
                CreateTable(
                    stable_id=branch_class.stable_id,
                    namespace=branch_class.namespace,
                    relname=branch_class.relname,
                    columns=branch.get_class_attributes(branch_class.stable_id),
                )
            )
            # Check if RLS needs to be enabled on the new table
            if branch_class.relrowsecurity:
                enable_rls_op = EnableRowLevelSecurity()
                changes.append(
                    AlterTable(
                        stable_id=branch_class.stable_id,
                        namespace=branch_class.namespace,
                        relname=branch_class.relname,
                        operation=enable_rls_op,
                    )
                )
            return changes

        case (master_class, None) if master_class is not None:
            # Class dropped
            changes.append(
                DropTable(
                    stable_id=master_class.stable_id,
                    namespace=master_class.namespace,
                    relname=master_class.relname,
                )
            )
            return changes

        case (master_class, branch_class) if (
            master_class is not None and branch_class is not None
        ):
            # Class exists in both - continue to check for modifications
            pass

        case (None, None):
            # Both are None - this shouldn't happen in normal operation
            # but it makes the type checker happy
            return changes

    # Class exists in both with same stable_id - check for changes
    # At this point, both master_class and branch_class are guaranteed to be not None
    assert master_class is not None and branch_class is not None
    class_metadata_changed = not master_class.semantic_equality(branch_class)

    # Check for RLS status changes (only for tables)
    if (
        master_class.relkind == "r"
        and branch_class.relkind == "r"
        and master_class.relrowsecurity != branch_class.relrowsecurity
    ):
        if branch_class.relrowsecurity:
            # Enable RLS using ALTER TABLE operation
            changes.append(
                AlterTable(
                    stable_id=branch_class.stable_id,
                    namespace=branch_class.namespace,
                    relname=branch_class.relname,
                    operation=EnableRowLevelSecurity(),
                )
            )
        else:
            # Disable RLS using ALTER TABLE operation
            changes.append(
                AlterTable(
                    stable_id=master_class.stable_id,
                    namespace=master_class.namespace,
                    relname=master_class.relname,
                    operation=DisableRowLevelSecurity(),
                )
            )

    # Always check for column changes even if class metadata is unchanged
    alter_changes = diff_class_columns(master, branch, master_class, branch_class)

    if class_metadata_changed or alter_changes:
        changes.extend(alter_changes)

    return changes


def diff_class_columns(
    master: PgCatalog, branch: PgCatalog, master_class: PgClass, branch_class: PgClass
) -> list[DDL]:
    """Diff columns between master and branch classes to generate ALTER operations."""
    changes: list[DDL] = []

    # Get columns for both classes
    master_columns = master.get_class_attributes(master_class.stable_id)
    branch_columns = branch.get_class_attributes(branch_class.stable_id)

    # Create column maps for efficient lookup
    master_col_map = {col.attname: col for col in master_columns}
    branch_col_map = {col.attname: col for col in branch_columns}

    # Find all column names across both classes, ordered by attnum to ensure consistent column ordering
    all_columns = []

    # Add all master columns
    for col in master_columns:
        all_columns.append((col.attname, col.attnum))

    # Add branch columns that aren't in master
    for col in branch_columns:
        if col.attname not in master_col_map:
            all_columns.append((col.attname, col.attnum))

    # Sort by attnum to ensure consistent ordering
    all_columns.sort(key=lambda x: x[1])

    for col_name, _ in all_columns:
        master_col = master_col_map.get(col_name)
        branch_col = branch_col_map.get(col_name)

        # Delegate all column comparison logic to diff_single_column
        column_changes = diff_single_column(
            master_class, branch_class, master_col, branch_col
        )
        changes.extend(column_changes)

    return changes


def diff_view_to_view(
    master: PgCatalog,
    branch: PgCatalog,
    master_class: PgClass | None,
    branch_class: PgClass | None,
) -> list[DDL]:
    """Handle view-to-view diff operations (create, drop, replace)."""
    changes: list[DDL] = []

    # Handle creation/deletion cases
    match (master_class, branch_class):
        case (None, branch_class) if branch_class is not None:
            # View created - use CreateView for new views
            view_definition = branch_class.view_definition or ""
            changes.append(
                CreateView(
                    stable_id=branch_class.stable_id,
                    namespace=branch_class.namespace,
                    relname=branch_class.relname,
                    definition=view_definition,
                )
            )
            return changes

        case (master_class, None) if master_class is not None:
            # View dropped
            changes.append(
                DropView(
                    stable_id=master_class.stable_id,
                    namespace=master_class.namespace,
                    relname=master_class.relname,
                )
            )
            return changes

        case (master_class, branch_class) if (
            master_class is not None and branch_class is not None
        ):
            # View exists in both - check for definition changes
            source_definition = master_class.view_definition or ""
            target_definition = branch_class.view_definition or ""

            # Compare normalized definitions (whitespace-insensitive comparison)
            if normalize_view_definition(
                source_definition
            ) != normalize_view_definition(target_definition):
                # TODO: Implement smart view change strategy
                # Currently we always use CREATE OR REPLACE VIEW, but this fails for structural changes.
                # We should:
                # 1. Analyze the view definition changes (column order, names, types)
                # 2. Determine if CREATE OR REPLACE VIEW will work
                # 3. If not, check for view dependencies using the catalog
                # 4. Choose appropriate strategy:
                #    - ALTER VIEW ALTER COLUMN for simple renames/type changes
                #    - DROP + CREATE if no dependencies
                #    - Exception with detailed guidance if dependencies exist
                #
                # Example exception message:
                # "Cannot modify view 'schema.view_name' because it reorders columns (position 5
                #  changed from 'created_at' to 'author_bio'), which requires DROP + CREATE.
                #  However, this view has dependencies: ['schema.dependent_view1', 'schema.dependent_view2'].
                #  Please manually handle this migration or restructure to avoid column reordering."
                changes.append(
                    ReplaceView(
                        stable_id=branch_class.stable_id,
                        namespace=branch_class.namespace,
                        relname=branch_class.relname,
                        definition=target_definition,
                    )
                )
            return changes
        case _:
            # Invalid case - return no changes
            return changes


def normalize_view_definition(definition: str) -> str:
    """Normalize view definition for comparison by removing extra whitespace and standardizing formatting."""
    # Remove extra whitespace and normalize spacing
    normalized = " ".join(definition.split())
    # Convert to lowercase for case-insensitive comparison
    return normalized.lower().strip()


def diff_single_column(
    master_class: PgClass | None,
    branch_class: PgClass | None,
    master_col: PgAttribute | None,
    branch_col: PgAttribute | None,
) -> list[DDL]:
    """Compare columns between master and branch to generate operations."""
    changes: list[DDL] = []

    # Handle column addition/removal
    match (master_col, branch_col):
        case (None, branch_col) if branch_col is not None and branch_class is not None:
            # Add new column - works for both regular and generated columns
            add_operation: ColumnOperation = AddColumn(column=branch_col)
            changes.append(
                AlterTable(
                    stable_id=branch_class.stable_id,
                    namespace=branch_class.namespace,
                    relname=branch_class.relname,
                    operation=add_operation,
                )
            )
            return changes

        case (master_col, None) if master_col is not None and master_class is not None:
            # Drop column - works for both regular and generated columns
            drop_operation: ColumnOperation = DropColumn(column_name=master_col.attname)
            changes.append(
                AlterTable(
                    stable_id=master_class.stable_id,
                    namespace=master_class.namespace,
                    relname=master_class.relname,
                    operation=drop_operation,
                )
            )
            return changes

        case (master_col, branch_col) if (
            master_col is not None
            and branch_col is not None
            and master_class is not None
            and branch_class is not None
        ):
            # Column exists in both - continue to check for changes
            pass
        case _:
            # Invalid case - return no changes
            return changes

    # Check for generated column changes first (requires drop+recreate)
    if master_col.is_generated != branch_col.is_generated or (
        master_col.is_generated
        and branch_col.is_generated
        and master_col.generated_expression != branch_col.generated_expression
    ):
        # Generated column changed - use drop + recreate
        changes.append(
            AlterTable(
                stable_id=branch_class.stable_id,
                namespace=branch_class.namespace,
                relname=branch_class.relname,
                operation=DropColumn(column_name=master_col.attname),
            )
        )
        changes.append(
            AlterTable(
                stable_id=branch_class.stable_id,
                namespace=branch_class.namespace,
                relname=branch_class.relname,
                operation=AddColumn(column=branch_col),
            )
        )
        # Return early since we've handled the column completely
        return changes

    # Check for type changes
    if master_col.formatted_type != branch_col.formatted_type:
        changes.append(
            AlterTable(
                stable_id=branch_class.stable_id,
                namespace=branch_class.namespace,
                relname=branch_class.relname,
                operation=AlterColumnType(
                    column_name=branch_col.attname,
                    new_type=branch_col.formatted_type,
                ),
            )
        )

    # Check for default value changes (skip for generated columns)
    if (
        not master_col.is_generated
        and not branch_col.is_generated
        and master_col.default_value != branch_col.default_value
    ):
        if branch_col.default_value is None:
            # Drop default
            changes.append(
                AlterTable(
                    stable_id=branch_class.stable_id,
                    namespace=branch_class.namespace,
                    relname=branch_class.relname,
                    operation=AlterColumnDropDefault(column_name=branch_col.attname),
                )
            )
        else:
            # Set default
            changes.append(
                AlterTable(
                    stable_id=branch_class.stable_id,
                    namespace=branch_class.namespace,
                    relname=branch_class.relname,
                    operation=AlterColumnSetDefault(
                        column_name=branch_col.attname,
                        default_expression=branch_col.default_value,
                    ),
                )
            )

    # Check for NOT NULL changes
    if master_col.attnotnull != branch_col.attnotnull:
        if branch_col.attnotnull:
            # Set NOT NULL
            changes.append(
                AlterTable(
                    stable_id=branch_class.stable_id,
                    namespace=branch_class.namespace,
                    relname=branch_class.relname,
                    operation=AlterColumnSetNotNull(column_name=branch_col.attname),
                )
            )
        else:
            # Drop NOT NULL
            changes.append(
                AlterTable(
                    stable_id=branch_class.stable_id,
                    namespace=branch_class.namespace,
                    relname=branch_class.relname,
                    operation=AlterColumnDropNotNull(column_name=branch_col.attname),
                )
            )

    return changes


def diff_materialized_view_to_materialized_view(
    master: PgCatalog,
    branch: PgCatalog,
    master_class: PgClass | None,
    branch_class: PgClass | None,
) -> list[DDL]:
    """Diff materialized view changes between catalogs.

    Materialized views follow similar patterns to regular views but with important differences:
    - No CREATE OR REPLACE MATERIALIZED VIEW (must DROP + CREATE)
    - Always create WITH NO DATA for safety during migrations
    - Data is not preserved during definition changes
    """
    changes: list[DDL] = []

    if master_class is None and branch_class is not None:
        # Create new materialized view
        if not branch_class.view_definition:
            raise ValueError(
                f"Materialized view {branch_class.stable_id} missing definition"
            )

        changes.append(
            CreateMaterializedView(
                stable_id=branch_class.stable_id,
                namespace=branch_class.namespace,
                relname=branch_class.relname,
                definition=branch_class.view_definition,
            )
        )
    elif master_class is not None and branch_class is None:
        # Drop materialized view
        changes.append(
            DropMaterializedView(
                stable_id=master_class.stable_id,
                namespace=master_class.namespace,
                relname=master_class.relname,
            )
        )
    elif master_class is not None and branch_class is not None:
        # Check if definition changed
        master_def = master_class.view_definition or ""
        branch_def = branch_class.view_definition or ""

        if master_def.strip() != branch_def.strip():
            # Replace materialized view (DROP + CREATE)
            # Unlike regular views, materialized views cannot use CREATE OR REPLACE
            if not branch_class.view_definition:
                raise ValueError(
                    f"Materialized view {branch_class.stable_id} missing definition"
                )

            changes.append(
                ReplaceMaterializedView(
                    stable_id=branch_class.stable_id,
                    namespace=branch_class.namespace,
                    relname=branch_class.relname,
                    definition=branch_class.view_definition,
                )
            )

    return changes
