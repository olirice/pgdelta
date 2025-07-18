"""ALTER TABLE SQL generation tests."""

import pytest

from pgdelta.changes import generate_sql
from pgdelta.changes.table import (
    AddColumn,
    AlterColumnDropDefault,
    AlterColumnDropNotNull,
    AlterColumnSetDefault,
    AlterColumnSetNotNull,
    AlterColumnType,
    AlterTable,
    DisableRowLevelSecurity,
    DropColumn,
    EnableRowLevelSecurity,
)
from pgdelta.model import PgAttribute


def test_alter_table_add_column():
    """Test ALTER TABLE ADD COLUMN generation."""
    column = PgAttribute(
        owner_namespace="public",
        owner_name="users",
        owner_relkind="r",
        attname="email",
        attnum=3,
        attnotnull=True,
        formatted_type="character varying(255)",
        attrelid=16384,
        default_value="'user@example.com'::character varying",
    )

    change = AlterTable(
        stable_id="r:public.users",
        namespace="public",
        relname="users",
        operation=AddColumn(column=column),
    )

    sql = generate_sql(change)
    expected = (
        'ALTER TABLE "public"."users" '
        'ADD COLUMN "email" character varying(255) NOT NULL '
        "DEFAULT 'user@example.com'::character varying;"
    )
    assert sql == expected


def test_alter_table_add_column_minimal():
    """Test ALTER TABLE ADD COLUMN with minimal attributes."""
    column = PgAttribute(
        owner_namespace="public",
        owner_name="users",
        owner_relkind="r",
        attname="simple_col",
        attnum=5,
        attnotnull=False,
        formatted_type="integer",
        attrelid=16384,
    )

    change = AlterTable(
        stable_id="r:public.users",
        namespace="public",
        relname="users",
        operation=AddColumn(column=column),
    )

    sql = generate_sql(change)
    assert sql == 'ALTER TABLE "public"."users" ADD COLUMN "simple_col" integer;'


def test_alter_table_drop_column():
    """Test ALTER TABLE DROP COLUMN generation."""
    change = AlterTable(
        stable_id="r:public.users",
        namespace="public",
        relname="users",
        operation=DropColumn(column_name="email"),
    )

    sql = generate_sql(change)
    assert sql == 'ALTER TABLE "public"."users" DROP COLUMN "email";'


def test_alter_table_alter_column_type():
    """Test ALTER TABLE ALTER COLUMN TYPE generation."""
    change = AlterTable(
        stable_id="r:public.users",
        namespace="public",
        relname="users",
        operation=AlterColumnType(
            column_name="age",
            new_type="bigint",
            using_expression="age::bigint",
        ),
    )

    sql = generate_sql(change)
    expected = (
        'ALTER TABLE "public"."users" ALTER COLUMN "age" TYPE bigint USING age::bigint;'
    )
    assert sql == expected


def test_alter_table_column_type_without_using():
    """Test ALTER COLUMN TYPE without USING expression."""
    change = AlterTable(
        stable_id="r:public.users",
        namespace="public",
        relname="users",
        operation=AlterColumnType(
            column_name="description",
            new_type="text",
        ),
    )

    sql = generate_sql(change)
    expected = 'ALTER TABLE "public"."users" ALTER COLUMN "description" TYPE text;'
    assert sql == expected


def test_alter_table_set_default():
    """Test ALTER TABLE ALTER COLUMN SET DEFAULT generation."""
    change = AlterTable(
        stable_id="r:public.users",
        namespace="public",
        relname="users",
        operation=AlterColumnSetDefault(
            column_name="created_at",
            default_expression="CURRENT_TIMESTAMP",
        ),
    )

    sql = generate_sql(change)
    expected = 'ALTER TABLE "public"."users" ALTER COLUMN "created_at" SET DEFAULT CURRENT_TIMESTAMP;'
    assert sql == expected


def test_alter_table_drop_default():
    """Test ALTER TABLE ALTER COLUMN DROP DEFAULT generation."""
    change = AlterTable(
        stable_id="r:public.users",
        namespace="public",
        relname="users",
        operation=AlterColumnDropDefault(column_name="created_at"),
    )

    sql = generate_sql(change)
    assert sql == 'ALTER TABLE "public"."users" ALTER COLUMN "created_at" DROP DEFAULT;'


def test_alter_table_set_not_null():
    """Test ALTER TABLE ALTER COLUMN SET NOT NULL generation."""
    change = AlterTable(
        stable_id="r:public.users",
        namespace="public",
        relname="users",
        operation=AlterColumnSetNotNull(column_name="email"),
    )

    sql = generate_sql(change)
    assert sql == 'ALTER TABLE "public"."users" ALTER COLUMN "email" SET NOT NULL;'


def test_alter_table_drop_not_null():
    """Test ALTER TABLE ALTER COLUMN DROP NOT NULL generation."""
    change = AlterTable(
        stable_id="r:public.users",
        namespace="public",
        relname="users",
        operation=AlterColumnDropNotNull(column_name="email"),
    )

    sql = generate_sql(change)
    assert sql == 'ALTER TABLE "public"."users" ALTER COLUMN "email" DROP NOT NULL;'


def test_alter_table_single_operation_focus():
    """Test that AlterTable now handles only single operations."""
    column = PgAttribute(
        owner_namespace="public",
        owner_name="users",
        owner_relkind="r",
        attname="status",
        attnum=4,
        attnotnull=False,
        formatted_type="text",
        attrelid=16384,
    )

    change = AlterTable(
        stable_id="r:public.users",
        namespace="public",
        relname="users",
        operation=AddColumn(column=column),
    )

    sql = generate_sql(change)
    expected = 'ALTER TABLE "public"."users" ADD COLUMN "status" text;'
    assert sql == expected


def test_alter_table_unknown_operation():
    """Test ALTER TABLE with unknown operation type raises error."""
    from pgdelta.changes.table.alter import _generate_operation_sql

    # Create a mock operation that doesn't match any known type
    class UnknownOperation:
        pass

    with pytest.raises(ValueError, match="Unknown operation type"):
        _generate_operation_sql(UnknownOperation())


def test_alter_table_add_generated_column():
    """Test ALTER TABLE ADD COLUMN for generated column."""
    column = PgAttribute(
        owner_namespace="public",
        owner_name="users",
        owner_relkind="r",
        attname="full_name",
        attnum=5,
        attnotnull=True,
        formatted_type="text",
        attrelid=16384,
        attgenerated="s",
        generated_expression="first_name || ' ' || last_name",
    )

    change = AlterTable(
        stable_id="r:public.users",
        namespace="public",
        relname="users",
        operation=AddColumn(column=column),
    )

    sql = generate_sql(change)
    expected = (
        'ALTER TABLE "public"."users" '
        "ADD COLUMN \"full_name\" text GENERATED ALWAYS AS (first_name || ' ' || last_name) STORED NOT NULL;"
    )
    assert sql == expected


def test_alter_table_add_generated_column_minimal():
    """Test ALTER TABLE ADD COLUMN for generated column without NOT NULL."""
    column = PgAttribute(
        owner_namespace="public",
        owner_name="calculations",
        owner_relkind="r",
        attname="computed_value",
        attnum=3,
        attnotnull=False,
        formatted_type="numeric",
        attrelid=16385,
        attgenerated="s",
        generated_expression="value_a * value_b",
    )

    change = AlterTable(
        stable_id="r:public.calculations",
        namespace="public",
        relname="calculations",
        operation=AddColumn(column=column),
    )

    sql = generate_sql(change)
    expected = (
        'ALTER TABLE "public"."calculations" '
        'ADD COLUMN "computed_value" numeric GENERATED ALWAYS AS (value_a * value_b) STORED;'
    )
    assert sql == expected


def test_alter_table_drop_generated_column():
    """Test ALTER TABLE DROP COLUMN for generated column."""
    change = AlterTable(
        stable_id="r:public.users",
        namespace="public",
        relname="users",
        operation=DropColumn(column_name="full_name"),
    )

    sql = generate_sql(change)
    assert sql == 'ALTER TABLE "public"."users" DROP COLUMN "full_name";'


def test_alter_table_enable_rls():
    """Test ALTER TABLE ENABLE ROW LEVEL SECURITY."""
    change = AlterTable(
        stable_id="r:public.users",
        namespace="public",
        relname="users",
        operation=EnableRowLevelSecurity(),
    )

    sql = generate_sql(change)

    assert sql == 'ALTER TABLE "public"."users" ENABLE ROW LEVEL SECURITY;'


def test_alter_table_disable_rls():
    """Test ALTER TABLE DISABLE ROW LEVEL SECURITY."""
    change = AlterTable(
        stable_id="r:public.users",
        namespace="public",
        relname="users",
        operation=DisableRowLevelSecurity(),
    )

    sql = generate_sql(change)

    assert sql == 'ALTER TABLE "public"."users" DISABLE ROW LEVEL SECURITY;'


def test_alter_table_enable_rls_complex_schema():
    """Test ENABLE RLS with complex schema and table names."""
    change = AlterTable(
        stable_id="r:auth.user_sessions",
        namespace="auth",
        relname="user_sessions",
        operation=EnableRowLevelSecurity(),
    )

    sql = generate_sql(change)

    assert sql == 'ALTER TABLE "auth"."user_sessions" ENABLE ROW LEVEL SECURITY;'


def test_alter_table_disable_rls_complex_schema():
    """Test DISABLE RLS with complex schema and table names."""
    change = AlterTable(
        stable_id="r:reporting.analytics_data",
        namespace="reporting",
        relname="analytics_data",
        operation=DisableRowLevelSecurity(),
    )

    sql = generate_sql(change)

    assert sql == 'ALTER TABLE "reporting"."analytics_data" DISABLE ROW LEVEL SECURITY;'
