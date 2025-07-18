"""Alter table change types and SQL generation.

PostgreSQL 17 ALTER TABLE Synopsis:
https://www.postgresql.org/docs/17/sql-altertable.html

ALTER TABLE [ IF EXISTS ] [ ONLY ] name [ * ]
    action [, ... ]
ALTER TABLE [ IF EXISTS ] [ ONLY ] name [ * ]
    RENAME [ COLUMN ] column_name TO new_column_name
ALTER TABLE [ IF EXISTS ] [ ONLY ] name [ * ]
    RENAME CONSTRAINT constraint_name TO new_constraint_name
ALTER TABLE [ IF EXISTS ] name
    RENAME TO new_name
ALTER TABLE [ IF EXISTS ] name
    SET SCHEMA new_schema
ALTER TABLE ALL IN TABLESPACE name [ OWNED BY role_name [, ... ] ]
    SET TABLESPACE new_tablespace [ NOWAIT ]
ALTER TABLE [ IF EXISTS ] name
    ATTACH PARTITION partition_name { FOR VALUES partition_bound_spec | DEFAULT }
ALTER TABLE [ IF EXISTS ] name
    DETACH PARTITION partition_name [ CONCURRENTLY | FINALIZE ]

where action is one of:

    ADD [ COLUMN ] [ IF NOT EXISTS ] column_name data_type [ COLLATE collation ] [ column_constraint [ ... ] ]
    DROP [ COLUMN ] [ IF EXISTS ] column_name [ RESTRICT | CASCADE ]
    ALTER [ COLUMN ] column_name [ SET DATA ] TYPE data_type [ COLLATE collation ] [ USING expression ]
    ALTER [ COLUMN ] column_name SET DEFAULT expression
    ALTER [ COLUMN ] column_name DROP DEFAULT
    ALTER [ COLUMN ] column_name { SET | DROP } NOT NULL
    ALTER [ COLUMN ] column_name DROP EXPRESSION [ IF EXISTS ]
    ALTER [ COLUMN ] column_name ADD GENERATED { ALWAYS | BY DEFAULT } AS IDENTITY [ ( sequence_options ) ]
    ALTER [ COLUMN ] column_name { SET GENERATED { ALWAYS | BY DEFAULT } | SET sequence_option | RESTART [ [ WITH ] restart ] } [...]
    ALTER [ COLUMN ] column_name DROP IDENTITY [ IF EXISTS ]
    ALTER [ COLUMN ] column_name SET STATISTICS integer
    ALTER [ COLUMN ] column_name SET ( attribute_option = value [, ... ] )
    ALTER [ COLUMN ] column_name RESET ( attribute_option [, ... ] )
    ALTER [ COLUMN ] column_name SET STORAGE { PLAIN | EXTERNAL | EXTENDED | MAIN | DEFAULT }
    ALTER [ COLUMN ] column_name SET COMPRESSION compression_method
    ADD table_constraint [ NOT VALID ]
    ADD table_constraint_using_index
    ALTER CONSTRAINT constraint_name [ DEFERRABLE | NOT DEFERRABLE ] [ INITIALLY DEFERRED | INITIALLY IMMEDIATE ]
    VALIDATE CONSTRAINT constraint_name
    DROP CONSTRAINT [ IF EXISTS ]  constraint_name [ RESTRICT | CASCADE ]
    DISABLE TRIGGER [ trigger_name | ALL | USER ]
    ENABLE TRIGGER [ trigger_name | ALL | USER ]
    ENABLE REPLICA TRIGGER trigger_name
    ENABLE ALWAYS TRIGGER trigger_name
    DISABLE RULE rewrite_rule_name
    ENABLE RULE rewrite_rule_name
    ENABLE REPLICA RULE rewrite_rule_name
    ENABLE ALWAYS RULE rewrite_rule_name
    DISABLE ROW LEVEL SECURITY
    ENABLE ROW LEVEL SECURITY
    FORCE ROW LEVEL SECURITY
    NO FORCE ROW LEVEL SECURITY
    CLUSTER ON index_name
    SET WITHOUT CLUSTER
    SET WITHOUT OIDS
    SET ACCESS METHOD new_access_method
    SET TABLESPACE new_tablespace
    SET { LOGGED | UNLOGGED }
    SET ( storage_parameter [= value] [, ... ] )
    RESET ( storage_parameter [, ... ] )
    INHERIT parent_table
    NO INHERIT parent_table
    OF type_name
    NOT OF
    OWNER TO { new_owner | CURRENT_ROLE | CURRENT_USER | SESSION_USER }
    REPLICA IDENTITY { DEFAULT | USING INDEX index_name | FULL | NOTHING }

Currently supported:
- ADD COLUMN with data type, NOT NULL, and DEFAULT
- DROP COLUMN
- ALTER COLUMN TYPE (with USING expression)
- ALTER COLUMN SET/DROP DEFAULT
- ALTER COLUMN SET/DROP NOT NULL

Intentionally not supported (not needed for DDL generation):
- CASCADE/RESTRICT options (dependency resolution handles ordering)
- ONLY keyword
- Constraint operations (PRIMARY KEY, FOREIGN KEY, CHECK, UNIQUE)
- COLLATE settings
- Column constraints beyond NOT NULL
- GENERATED columns
- STATISTICS settings
- Column attribute options
- Trigger operations
- Rule operations
- Row-level security
- Clustering
- Access method changes
- Storage parameters
- Inheritance changes
- Type operations
- Owner changes
- Replica identity
- Partitioning operations
- LOGGED/UNLOGGED changes (storage detail that changes automatically)

Intentionally not supported (not needed for DDL generation):
- IF EXISTS clauses (pgdelta tracks existence, so always knows if objects exist)
- Table renaming (indistinguishable from drop/create - always use drop/create path)
- Column renaming (indistinguishable from drop/create - always use drop/create path)
- Schema changes (changes stable_id, always use drop/create path)
- STORAGE settings (storage details that change automatically)
- COMPRESSION settings (storage details that change automatically)
- Tablespace changes (storage location is not schema structure)
"""

from dataclasses import dataclass

from ...model import PgAttribute


@dataclass(frozen=True)
class AddColumn:
    """Add column to table."""

    column: PgAttribute


@dataclass(frozen=True)
class DropColumn:
    """Drop column from table."""

    column_name: str


@dataclass(frozen=True)
class AlterColumnType:
    """Alter column data type."""

    column_name: str
    new_type: str
    using_expression: str | None = None


@dataclass(frozen=True)
class AlterColumnSetDefault:
    """Set column default value."""

    column_name: str
    default_expression: str


@dataclass(frozen=True)
class AlterColumnDropDefault:
    """Drop column default value."""

    column_name: str


@dataclass(frozen=True)
class AlterColumnSetNotNull:
    """Set column NOT NULL constraint."""

    column_name: str


@dataclass(frozen=True)
class AlterColumnDropNotNull:
    """Drop column NOT NULL constraint."""

    column_name: str


@dataclass(frozen=True)
class EnableRowLevelSecurity:
    """Enable row level security on table."""

    pass  # No additional parameters needed


@dataclass(frozen=True)
class DisableRowLevelSecurity:
    """Disable row level security on table."""

    pass  # No additional parameters needed


# Union type for all table operations (including column operations and table-level operations)
TableOperation = (
    AddColumn
    | DropColumn
    | AlterColumnType
    | AlterColumnSetDefault
    | AlterColumnDropDefault
    | AlterColumnSetNotNull
    | AlterColumnDropNotNull
    | EnableRowLevelSecurity
    | DisableRowLevelSecurity
)

# Backward compatibility alias
ColumnOperation = TableOperation


@dataclass(frozen=True)
class AlterTable:
    """Alter table change."""

    stable_id: str
    namespace: str
    relname: str
    operation: ColumnOperation


def generate_alter_table_sql(change: AlterTable) -> str:
    """Generate ALTER TABLE SQL."""
    quoted_schema = f'"{change.namespace}"'
    quoted_table = f'"{change.relname}"'

    operation_sql = _generate_operation_sql(change.operation)
    return f"ALTER TABLE {quoted_schema}.{quoted_table} {operation_sql};"


def _generate_operation_sql(operation: ColumnOperation) -> str:
    """Generate SQL for a single column operation."""
    match operation:
        case AddColumn(column=col):
            col_def = f'ADD COLUMN "{col.attname}" {col.formatted_type}'
            if col.is_generated:
                col_def += f" GENERATED ALWAYS AS ({col.generated_expression}) STORED"
            if col.attnotnull:
                col_def += " NOT NULL"
            if (
                col.default_value and not col.is_generated
            ):  # Generated columns don't have defaults
                col_def += f" DEFAULT {col.default_value}"
            return col_def

        case DropColumn(column_name=name):
            return f'DROP COLUMN "{name}"'

        case AlterColumnType(
            column_name=name, new_type=new_type, using_expression=using
        ):
            sql = f'ALTER COLUMN "{name}" TYPE {new_type}'
            if using:
                sql += f" USING {using}"
            return sql

        case AlterColumnSetDefault(column_name=name, default_expression=default):
            return f'ALTER COLUMN "{name}" SET DEFAULT {default}'

        case AlterColumnDropDefault(column_name=name):
            return f'ALTER COLUMN "{name}" DROP DEFAULT'

        case AlterColumnSetNotNull(column_name=name):
            return f'ALTER COLUMN "{name}" SET NOT NULL'

        case AlterColumnDropNotNull(column_name=name):
            return f'ALTER COLUMN "{name}" DROP NOT NULL'

        case EnableRowLevelSecurity():
            return "ENABLE ROW LEVEL SECURITY"

        case DisableRowLevelSecurity():
            return "DISABLE ROW LEVEL SECURITY"

        case _:
            raise ValueError(f"Unknown operation type: {type(operation)}")
