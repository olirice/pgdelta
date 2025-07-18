"""Trigger SQL generation tests."""

import pytest

from pgdelta.changes.dispatcher import generate_sql
from pgdelta.changes.trigger import CreateTrigger, DropTrigger
from pgdelta.model.pg_trigger import PgTrigger


def test_create_trigger_basic():
    """Test basic CREATE TRIGGER SQL generation."""
    trigger = PgTrigger(
        tgname="update_timestamp",
        namespace="public",
        table_name="users",
        trigger_definition="CREATE TRIGGER update_timestamp BEFORE UPDATE ON public.users FOR EACH ROW EXECUTE FUNCTION update_timestamp_func()",
        oid=16384,
        tgrelid=16385,
        tgfoid=16386,
    )

    change = CreateTrigger(trigger=trigger)
    sql = generate_sql(change)

    assert "CREATE TRIGGER update_timestamp" in sql
    assert "BEFORE UPDATE ON public.users" in sql
    assert "EXECUTE FUNCTION update_timestamp_func()" in sql
    assert sql.endswith(";")


def test_create_trigger_complex():
    """Test complex CREATE TRIGGER with multiple events and conditions."""
    trigger = PgTrigger(
        tgname="audit_trigger",
        namespace="audit",
        table_name="sensitive_table",
        trigger_definition="""CREATE TRIGGER audit_trigger AFTER INSERT OR UPDATE OR DELETE ON audit.sensitive_table FOR EACH ROW WHEN (pg_trigger_depth() = 0) EXECUTE FUNCTION audit.log_changes()""",
        oid=16387,
        tgrelid=16388,
        tgfoid=16389,
    )

    change = CreateTrigger(trigger=trigger)
    sql = generate_sql(change)

    assert "CREATE TRIGGER audit_trigger" in sql
    assert "AFTER INSERT OR UPDATE OR DELETE" in sql
    assert "WHEN (pg_trigger_depth() = 0)" in sql
    assert "audit.log_changes()" in sql
    assert sql.endswith(";")


def test_create_trigger_instead_of():
    """Test INSTEAD OF trigger on a view."""
    trigger = PgTrigger(
        tgname="view_insert_trigger",
        namespace="public",
        table_name="user_view",
        trigger_definition="CREATE TRIGGER view_insert_trigger INSTEAD OF INSERT ON public.user_view FOR EACH ROW EXECUTE FUNCTION handle_view_insert()",
        oid=16390,
        tgrelid=16391,
        tgfoid=16392,
    )

    change = CreateTrigger(trigger=trigger)
    sql = generate_sql(change)

    assert "CREATE TRIGGER view_insert_trigger" in sql
    assert "INSTEAD OF INSERT" in sql
    assert "ON public.user_view" in sql
    assert sql.endswith(";")


def test_create_trigger_with_semicolon_in_definition():
    """Test trigger definition that already includes semicolon."""
    trigger = PgTrigger(
        tgname="complex_trigger",
        namespace="test",
        table_name="test_table",
        trigger_definition="CREATE TRIGGER complex_trigger BEFORE INSERT ON test.test_table FOR EACH ROW EXECUTE FUNCTION test_func();",
        oid=16393,
        tgrelid=16394,
        tgfoid=16395,
    )

    change = CreateTrigger(trigger=trigger)
    sql = generate_sql(change)

    # Should not add double semicolon
    assert sql.endswith(";")
    assert not sql.endswith(";;")


def test_drop_trigger_basic():
    """Test basic DROP TRIGGER SQL generation."""
    trigger = PgTrigger(
        tgname="old_trigger",
        namespace="public",
        table_name="users",
        trigger_definition="CREATE TRIGGER old_trigger BEFORE UPDATE ON public.users FOR EACH ROW EXECUTE FUNCTION old_func()",
        oid=16396,
        tgrelid=16397,
        tgfoid=16398,
    )

    change = DropTrigger(trigger=trigger)
    sql = generate_sql(change)

    assert 'DROP TRIGGER "old_trigger" ON "public"."users"' in sql
    assert sql.endswith(";")


def test_drop_trigger_with_special_characters():
    """Test DROP TRIGGER with special characters in names."""
    trigger = PgTrigger(
        tgname="trigger-with-dash",
        namespace="test-schema",
        table_name="table with space",
        trigger_definition='CREATE TRIGGER "trigger-with-dash" BEFORE UPDATE ON "test-schema"."table with space" FOR EACH ROW EXECUTE FUNCTION test_func()',
        oid=16399,
        tgrelid=16400,
        tgfoid=16401,
    )

    change = DropTrigger(trigger=trigger)
    sql = generate_sql(change)

    assert 'DROP TRIGGER "trigger-with-dash"' in sql
    assert 'ON "test-schema"."table with space"' in sql
    assert sql.endswith(";")


@pytest.mark.parametrize(
    "trigger_name,namespace,table_name,expected_quoted_name,expected_quoted_table",
    [
        ("simple", "public", "users", '"simple"', '"public"."users"'),
        (
            "trigger-dash",
            "schema-dash",
            "table-dash",
            '"trigger-dash"',
            '"schema-dash"."table-dash"',
        ),
        (
            "trigger_underscore",
            "schema_underscore",
            "table_underscore",
            '"trigger_underscore"',
            '"schema_underscore"."table_underscore"',
        ),
        (
            "trigger space",
            "schema space",
            "table space",
            '"trigger space"',
            '"schema space"."table space"',
        ),
        (
            "TRIGGER_CAPS",
            "SCHEMA_CAPS",
            "TABLE_CAPS",
            '"TRIGGER_CAPS"',
            '"SCHEMA_CAPS"."TABLE_CAPS"',
        ),
    ],
)
def test_trigger_name_quoting(
    trigger_name, namespace, table_name, expected_quoted_name, expected_quoted_table
):
    """Test that trigger, schema, and table names are properly quoted."""
    trigger = PgTrigger(
        tgname=trigger_name,
        namespace=namespace,
        table_name=table_name,
        trigger_definition=f"CREATE TRIGGER {trigger_name} BEFORE UPDATE ON {namespace}.{table_name} FOR EACH ROW EXECUTE FUNCTION test_func()",
        oid=16402,
        tgrelid=16403,
        tgfoid=16404,
    )

    change = DropTrigger(trigger=trigger)
    sql = generate_sql(change)

    assert expected_quoted_name in sql
    assert expected_quoted_table in sql


def test_trigger_stable_id():
    """Test trigger stable_id property."""
    trigger = PgTrigger(
        tgname="test_trigger",
        namespace="test_schema",
        table_name="test_table",
        trigger_definition="CREATE TRIGGER test_trigger BEFORE UPDATE ON test_schema.test_table FOR EACH ROW EXECUTE FUNCTION test_func()",
        oid=16405,
        tgrelid=16406,
        tgfoid=16407,
    )

    assert trigger.stable_id == "trigger:test_schema.test_table.test_trigger"


def test_create_trigger_change_properties():
    """Test CreateTrigger change properties."""
    trigger = PgTrigger(
        tgname="test_trigger",
        namespace="test_schema",
        table_name="test_table",
        trigger_definition="CREATE TRIGGER test_trigger BEFORE UPDATE ON test_schema.test_table FOR EACH ROW EXECUTE FUNCTION test_func()",
        oid=16411,
        tgrelid=16412,
        tgfoid=16413,
    )

    change = CreateTrigger(trigger=trigger)

    assert change.stable_id == "trigger:test_schema.test_table.test_trigger"


def test_drop_trigger_change_properties():
    """Test DropTrigger change properties."""
    trigger = PgTrigger(
        tgname="test_trigger",
        namespace="test_schema",
        table_name="test_table",
        trigger_definition="CREATE TRIGGER test_trigger BEFORE UPDATE ON test_schema.test_table FOR EACH ROW EXECUTE FUNCTION test_func()",
        oid=16414,
        tgrelid=16415,
        tgfoid=16416,
    )

    change = DropTrigger(trigger=trigger)

    assert change.stable_id == "trigger:test_schema.test_table.test_trigger"
