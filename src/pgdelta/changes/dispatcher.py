"""SQL generation dispatcher."""

import logging
from typing import NoReturn

from .constraint import (
    AlterConstraint,
    CreateConstraint,
    DropConstraint,
    generate_alter_constraint_sql,
    generate_create_constraint_sql,
    generate_drop_constraint_sql,
)
from .function import (
    CreateFunction,
    DropFunction,
    ReplaceFunction,
    generate_create_function_sql,
    generate_drop_function_sql,
    generate_replace_function_sql,
)
from .index import (
    AlterIndex,
    CreateIndex,
    DropIndex,
    generate_create_index_sql,
    generate_drop_index_sql,
)
from .materialized_view import (
    CreateMaterializedView,
    DropMaterializedView,
    ReplaceMaterializedView,
    generate_create_materialized_view_sql,
    generate_drop_materialized_view_sql,
    generate_replace_materialized_view_sql,
)
from .policy import (
    AlterPolicy,
    CreatePolicy,
    DropPolicy,
    RenamePolicyTo,
    generate_alter_policy_sql,
    generate_create_policy_sql,
    generate_drop_policy_sql,
    generate_rename_policy_sql,
)
from .schema import (
    CreateSchema,
    DropSchema,
)
from .schema.create import generate_create_schema_sql
from .schema.drop import generate_drop_schema_sql
from .sequence import (
    AlterSequence,
    CreateSequence,
    DropSequence,
    generate_alter_sequence_sql,
    generate_create_sequence_sql,
    generate_drop_sequence_sql,
)
from .table import (
    AlterTable,
    CreateTable,
    DropTable,
    generate_alter_table_sql,
    generate_create_table_sql,
    generate_drop_table_sql,
)
from .trigger import (
    CreateTrigger,
    DropTrigger,
)
from .trigger.create import generate_create_trigger_sql
from .trigger.drop import generate_drop_trigger_sql
from .type import (
    AlterTypeAddAttribute,
    AlterTypeAddValue,
    AlterTypeAlterAttribute,
    AlterTypeDropAttribute,
    AlterTypeOwnerTo,
    AlterTypeRename,
    AlterTypeRenameValue,
    AlterTypeSetSchema,
    CreateType,
    DropType,
)
from .type.alter import generate_alter_type_sql
from .type.create import generate_create_type_sql
from .type.drop import generate_drop_type_sql
from .view import (
    CreateView,
    DropView,
    ReplaceView,
    generate_create_view_sql,
    generate_drop_view_sql,
    generate_replace_view_sql,
)

logger = logging.getLogger(__name__)

# DDL (Data Definition Language) type definitions
# Avoids confusion between 'schema' entity and database schema structure

DDLCreate = (
    CreateSchema
    | CreateTable
    | CreateView
    | CreateMaterializedView
    | CreateConstraint
    | CreateFunction
    | CreateIndex
    | CreateSequence
    | CreatePolicy
    | CreateTrigger
    | CreateType
)

DDLDrop = (
    DropSchema
    | DropTable
    | DropView
    | DropMaterializedView
    | DropConstraint
    | DropFunction
    | DropIndex
    | DropSequence
    | DropPolicy
    | DropTrigger
    | DropType
)

DDLAlter = (
    AlterTable
    | AlterConstraint
    | AlterIndex
    | AlterSequence
    | AlterPolicy
    | RenamePolicyTo
    | AlterTypeOwnerTo
    | AlterTypeRename
    | AlterTypeSetSchema
    | AlterTypeAddAttribute
    | AlterTypeDropAttribute
    | AlterTypeAlterAttribute
    | AlterTypeAddValue
    | AlterTypeRenameValue
)

DDLReplace = ReplaceView | ReplaceFunction | ReplaceMaterializedView

# Main DDL union type for all database structure changes
DDL = DDLCreate | DDLDrop | DDLAlter | DDLReplace


def assert_never(value: NoReturn) -> NoReturn:
    """Assert that this code is never reached."""
    raise AssertionError(f"Unhandled value: {value}")


def is_drop_change(change: DDL) -> bool:
    """Determine if a change is a DROP operation."""
    return isinstance(change, DDLDrop)


def is_create_change(change: DDL) -> bool:
    """Determine if a change is a CREATE operation."""
    return isinstance(change, DDLCreate)


def is_replace_change(change: DDL) -> bool:
    """Determine if a change is a REPLACE operation."""
    return isinstance(change, DDLReplace)


def is_alter_change(change: DDL) -> bool:
    """Determine if a change is an ALTER operation."""
    return isinstance(change, DDLAlter)


def generate_sql(change: DDL) -> str:
    """Generate SQL for a DDL change."""
    sql = ""

    match change:
        case CreateSchema():
            sql = generate_create_schema_sql(change)
        case DropSchema():
            sql = generate_drop_schema_sql(change)
        case CreateTable():
            sql = generate_create_table_sql(change)
        case DropTable():
            sql = generate_drop_table_sql(change)
        case AlterTable():
            sql = generate_alter_table_sql(change)
        case CreateView():
            sql = generate_create_view_sql(change)
        case DropView():
            sql = generate_drop_view_sql(change)
        case ReplaceView():
            sql = generate_replace_view_sql(change)
        case CreateMaterializedView():
            sql = generate_create_materialized_view_sql(change)
        case DropMaterializedView():
            sql = generate_drop_materialized_view_sql(change)
        case ReplaceMaterializedView():
            sql = generate_replace_materialized_view_sql(change)
        case CreateConstraint():
            sql = generate_create_constraint_sql(change)
        case DropConstraint():
            sql = generate_drop_constraint_sql(change)
        case AlterConstraint():
            sql = generate_alter_constraint_sql(change)
        case CreateFunction():
            sql = generate_create_function_sql(change)
        case DropFunction():
            sql = generate_drop_function_sql(change)
        case ReplaceFunction():
            sql = generate_replace_function_sql(change)
        case CreateIndex():
            sql = generate_create_index_sql(change)
        case DropIndex():
            sql = generate_drop_index_sql(change)
        case AlterIndex():
            raise NotImplementedError("ALTER INDEX operations are not yet implemented")
        case CreateSequence():
            sql = generate_create_sequence_sql(change)
        case DropSequence():
            sql = generate_drop_sequence_sql(change)
        case AlterSequence():
            sql = generate_alter_sequence_sql(change)
        case CreatePolicy():
            sql = generate_create_policy_sql(change)
        case DropPolicy():
            sql = generate_drop_policy_sql(change)
        case AlterPolicy():
            sql = generate_alter_policy_sql(change)
        case RenamePolicyTo():
            sql = generate_rename_policy_sql(change)
        case CreateTrigger():
            sql = generate_create_trigger_sql(change)
        case DropTrigger():
            sql = generate_drop_trigger_sql(change)
        case CreateType():
            sql = generate_create_type_sql(change)
        case DropType():
            sql = generate_drop_type_sql(change)
        case (
            AlterTypeOwnerTo()
            | AlterTypeRename()
            | AlterTypeSetSchema()
            | AlterTypeAddAttribute()
            | AlterTypeDropAttribute()
            | AlterTypeAlterAttribute()
            | AlterTypeAddValue()
            | AlterTypeRenameValue()
        ):
            sql = generate_alter_type_sql(change)
        case _:
            assert_never(change)

    # Log SQL generation
    logger.debug(
        "sql.generated",
        extra={
            "change_type": type(change).__name__,
            "stable_id": getattr(change, "stable_id", None),
            "sql": sql,
        },
    )

    return sql
