"""SQL generation dispatcher tests."""

from pgdelta.changes.constraint import AlterConstraint
from pgdelta.changes.dispatcher import generate_sql
from pgdelta.changes.index import AlterIndex
from pgdelta.changes.schema import CreateSchema
from pgdelta.changes.table import AlterColumnSetNotNull, AlterTable
from pgdelta.changes.view import DropView, ReplaceView
from pgdelta.model.pg_constraint import PgConstraint
from pgdelta.model.pg_index import PgIndex


def test_generate_sql_dispatcher_coverage():
    """Test that generate_sql dispatcher handles all change types correctly."""
    # Test schema change
    schema_change = CreateSchema(
        stable_id="test_schema",
        nspname="test_schema",
    )
    schema_sql = generate_sql(schema_change)
    assert 'CREATE SCHEMA "test_schema"' in schema_sql

    # Test alter table change
    alter_change = AlterTable(
        stable_id="r:test_schema.users",
        namespace="test_schema",
        relname="users",
        operation=AlterColumnSetNotNull(column_name="email"),
    )
    alter_sql = generate_sql(alter_change)
    assert 'ALTER TABLE "test_schema"."users"' in alter_sql
    assert "SET NOT NULL" in alter_sql

    # Test view drop change
    drop_view_change = DropView(
        stable_id="v:test_schema.user_summary",
        namespace="test_schema",
        relname="user_summary",
    )
    drop_view_sql = generate_sql(drop_view_change)
    assert 'DROP VIEW "test_schema"."user_summary"' in drop_view_sql

    # Test view replace change
    replace_view_change = ReplaceView(
        stable_id="v:test_schema.active_users",
        namespace="test_schema",
        relname="active_users",
        definition="SELECT * FROM users WHERE active = true",
    )
    replace_view_sql = generate_sql(replace_view_change)
    assert 'CREATE OR REPLACE VIEW "test_schema"."active_users"' in replace_view_sql
    assert "SELECT * FROM users WHERE active = true" in replace_view_sql


def test_generate_sql_alter_constraint():
    """Test dispatcher handles AlterConstraint changes - covers line 113."""
    old_constraint = PgConstraint(
        oid=12345,
        conname="test_fkey",
        connamespace=2200,
        conrelid=54321,
        contype="f",
        condeferrable=False,
        condeferred=False,
        convalidated=True,
        contypid=0,
        conindid=0,
        conparentid=0,
        confrelid=54322,
        confupdtype="a",
        confdeltype="a",
        confmatchtype="s",
        conislocal=True,
        coninhcount=0,
        connoinherit=False,
        conkey=[1],
        confkey=[1],
        conpfeqop=[96],
        conppeqop=[96],
        conffeqop=[96],
        conexclop=[],
        conbin=None,
        conpredicate=None,
        namespace_name="test_schema",
        table_name="test_table",
    )

    new_constraint = PgConstraint(
        oid=12345,
        conname="test_fkey",
        connamespace=2200,
        conrelid=54321,
        contype="f",
        condeferrable=True,  # Changed to deferrable
        condeferred=True,
        convalidated=True,
        contypid=0,
        conindid=0,
        conparentid=0,
        confrelid=54322,
        confupdtype="a",
        confdeltype="a",
        confmatchtype="s",
        conislocal=True,
        coninhcount=0,
        connoinherit=False,
        conkey=[1],
        confkey=[1],
        conpfeqop=[96],
        conppeqop=[96],
        conffeqop=[96],
        conexclop=[],
        conbin=None,
        conpredicate=None,
        namespace_name="test_schema",
        table_name="test_table",
    )

    alter_constraint_change = AlterConstraint(
        stable_id="test_schema.test_table.test_fkey",
        old_constraint=old_constraint,
        new_constraint=new_constraint,
        table_columns=[],
        referenced_table_columns=[],
    )

    sql = generate_sql(alter_constraint_change)
    assert 'ALTER TABLE "test_schema"."test_table"' in sql
    assert "ALTER CONSTRAINT" in sql
    assert "DEFERRABLE" in sql


def test_generate_sql_alter_index():
    """Test dispatcher handles AlterIndex changes - covers line 118."""
    old_index = PgIndex(
        name="test_idx",
        namespace_name="test_schema",
        table_name="test_table",
        is_unique=False,
        is_primary=False,
        is_constraint_index=False,
        index_definition="CREATE INDEX test_idx ON test_schema.test_table (id)",
        oid=12345,
        table_oid=54321,
    )

    new_index = PgIndex(
        name="test_idx",
        namespace_name="test_schema",
        table_name="test_table",
        is_unique=True,  # Changed to unique
        is_primary=False,
        is_constraint_index=False,
        index_definition="CREATE UNIQUE INDEX test_idx ON test_schema.test_table (id)",
        oid=12345,
        table_oid=54321,
    )

    alter_index_change = AlterIndex(
        stable_id="i:test_schema.test_idx",
        old_index=old_index,
        new_index=new_index,
    )

    try:
        generate_sql(alter_index_change)
        raise AssertionError("Should have raised NotImplementedError")
    except NotImplementedError as e:
        assert "ALTER INDEX operations are not yet implemented" in str(e)
