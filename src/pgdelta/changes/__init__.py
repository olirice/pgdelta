"""Change types and SQL generation."""

from .dispatcher import (
    DDL,
    generate_sql,
    is_create_change,
    is_drop_change,
    is_replace_change,
)
from .function import CreateFunction, DropFunction, ReplaceFunction
from .index import AlterIndex, CreateIndex, DropIndex
from .materialized_view import (
    CreateMaterializedView,
    DropMaterializedView,
    ReplaceMaterializedView,
)
from .policy import AlterPolicy, CreatePolicy, DropPolicy, RenamePolicyTo
from .schema import CreateSchema, DropSchema
from .sequence import AlterSequence, CreateSequence, DropSequence
from .table import (
    AddColumn,
    AlterColumnDropDefault,
    AlterColumnDropNotNull,
    AlterColumnSetDefault,
    AlterColumnSetNotNull,
    AlterColumnType,
    AlterTable,
    ColumnOperation,
    CreateTable,
    DisableRowLevelSecurity,
    DropColumn,
    DropTable,
    EnableRowLevelSecurity,
)
from .trigger import CreateTrigger, DropTrigger
from .type import CreateType, DropType
from .view import CreateView, DropView, ReplaceView

__all__ = [
    "DDL",
    "AddColumn",
    "AlterColumnDropDefault",
    "AlterColumnDropNotNull",
    "AlterColumnSetDefault",
    "AlterColumnSetNotNull",
    "AlterColumnType",
    "AlterIndex",
    "AlterPolicy",
    "AlterSequence",
    "AlterTable",
    "ColumnOperation",
    "CreateFunction",
    "CreateIndex",
    "CreateMaterializedView",
    "CreatePolicy",
    "CreateSchema",
    "CreateSequence",
    "CreateTable",
    "CreateTrigger",
    "CreateType",
    "CreateView",
    "DisableRowLevelSecurity",
    "DropColumn",
    "DropFunction",
    "DropIndex",
    "DropMaterializedView",
    "DropPolicy",
    "DropSchema",
    "DropSequence",
    "DropTable",
    "DropTrigger",
    "DropType",
    "DropView",
    "EnableRowLevelSecurity",
    "RenamePolicyTo",
    "ReplaceFunction",
    "ReplaceMaterializedView",
    "ReplaceView",
    "generate_sql",
    "is_create_change",
    "is_drop_change",
    "is_replace_change",
]
