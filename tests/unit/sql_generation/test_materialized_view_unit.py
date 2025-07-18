"""Materialized view SQL generation tests."""

import pytest

from pgdelta.changes.dispatcher import generate_sql
from pgdelta.changes.materialized_view import (
    CreateMaterializedView,
    DropMaterializedView,
    ReplaceMaterializedView,
)


def test_create_materialized_view_basic():
    """Test basic CREATE MATERIALIZED VIEW SQL generation."""
    change = CreateMaterializedView(
        stable_id="m:public.user_summary",
        namespace="public",
        relname="user_summary",
        definition="SELECT id, name, email FROM users WHERE active = true",
    )

    sql = generate_sql(change)

    assert 'CREATE MATERIALIZED VIEW "public"."user_summary"' in sql
    assert "SELECT id, name, email FROM users WHERE active = true" in sql
    assert "WITH NO DATA" in sql
    assert sql.endswith(";")


def test_create_materialized_view_complex():
    """Test complex CREATE MATERIALIZED VIEW with complex query."""
    change = CreateMaterializedView(
        stable_id="m:analytics.monthly_sales",
        namespace="analytics",
        relname="monthly_sales",
        definition="""SELECT
            DATE_TRUNC('month', sale_date) as month,
            COUNT(*) as total_sales,
            SUM(amount) as total_revenue,
            AVG(amount) as avg_sale
        FROM sales s
        JOIN customers c ON s.customer_id = c.id
        WHERE s.status = 'completed'
        GROUP BY DATE_TRUNC('month', sale_date)""",
    )

    sql = generate_sql(change)

    assert 'CREATE MATERIALIZED VIEW "analytics"."monthly_sales"' in sql
    assert "DATE_TRUNC('month', sale_date)" in sql
    assert "GROUP BY DATE_TRUNC('month', sale_date)" in sql
    assert "WITH NO DATA" in sql
    assert sql.endswith(";")


def test_create_materialized_view_with_special_characters():
    """Test CREATE MATERIALIZED VIEW with special characters in names."""
    change = CreateMaterializedView(
        stable_id="m:test-schema.user-summary",
        namespace="test-schema",
        relname="user-summary",
        definition="SELECT id, name FROM users",
    )

    sql = generate_sql(change)

    assert 'CREATE MATERIALIZED VIEW "test-schema"."user-summary"' in sql
    assert "SELECT id, name FROM users" in sql
    assert "WITH NO DATA" in sql
    assert sql.endswith(";")


def test_drop_materialized_view_basic():
    """Test basic DROP MATERIALIZED VIEW SQL generation."""
    change = DropMaterializedView(
        stable_id="m:public.old_summary",
        namespace="public",
        relname="old_summary",
    )

    sql = generate_sql(change)

    assert sql == 'DROP MATERIALIZED VIEW "public"."old_summary";'


def test_drop_materialized_view_with_special_characters():
    """Test DROP MATERIALIZED VIEW with special characters in names."""
    change = DropMaterializedView(
        stable_id="m:test-schema.old-summary",
        namespace="test-schema",
        relname="old-summary",
    )

    sql = generate_sql(change)

    assert sql == 'DROP MATERIALIZED VIEW "test-schema"."old-summary";'


def test_replace_materialized_view_basic():
    """Test basic REPLACE MATERIALIZED VIEW SQL generation (DROP + CREATE)."""
    change = ReplaceMaterializedView(
        stable_id="m:public.user_summary",
        namespace="public",
        relname="user_summary",
        definition="SELECT id, name, email, created_at FROM users WHERE active = true",
    )

    sql = generate_sql(change)

    # Should contain both DROP and CREATE statements
    assert 'DROP MATERIALIZED VIEW "public"."user_summary";' in sql
    assert 'CREATE MATERIALIZED VIEW "public"."user_summary"' in sql
    assert "SELECT id, name, email, created_at FROM users WHERE active = true" in sql
    assert "WITH NO DATA" in sql

    # Should be on separate lines
    lines = sql.split("\n")
    assert len(lines) == 2
    assert lines[0].startswith("DROP MATERIALIZED VIEW")
    assert lines[1].startswith("CREATE MATERIALIZED VIEW")


def test_replace_materialized_view_complex():
    """Test complex REPLACE MATERIALIZED VIEW with CTE and window functions."""
    change = ReplaceMaterializedView(
        stable_id="m:analytics.customer_rankings",
        namespace="analytics",
        relname="customer_rankings",
        definition="""WITH customer_stats AS (
            SELECT
                customer_id,
                COUNT(*) as order_count,
                SUM(amount) as total_spent
            FROM orders
            GROUP BY customer_id
        )
        SELECT
            c.id,
            c.name,
            cs.order_count,
            cs.total_spent,
            ROW_NUMBER() OVER (ORDER BY cs.total_spent DESC) as rank
        FROM customers c
        JOIN customer_stats cs ON c.id = cs.customer_id""",
    )

    sql = generate_sql(change)

    # Verify structure
    assert 'DROP MATERIALIZED VIEW "analytics"."customer_rankings";' in sql
    assert 'CREATE MATERIALIZED VIEW "analytics"."customer_rankings"' in sql
    assert "WITH customer_stats AS" in sql
    assert "ROW_NUMBER() OVER" in sql
    assert "WITH NO DATA" in sql


@pytest.mark.parametrize(
    "namespace,relname,expected_quoted",
    [
        ("public", "simple", '"public"."simple"'),
        ("test-schema", "view-name", '"test-schema"."view-name"'),
        (
            "schema_underscore",
            "view_underscore",
            '"schema_underscore"."view_underscore"',
        ),
        ("schema space", "view space", '"schema space"."view space"'),
        ("SCHEMA_CAPS", "VIEW_CAPS", '"SCHEMA_CAPS"."VIEW_CAPS"'),
    ],
)
def test_materialized_view_name_quoting(namespace, relname, expected_quoted):
    """Test that schema and view names are properly quoted."""
    create_change = CreateMaterializedView(
        stable_id=f"m:{namespace}.{relname}",
        namespace=namespace,
        relname=relname,
        definition="SELECT 1",
    )

    create_sql = generate_sql(create_change)
    assert expected_quoted in create_sql

    drop_change = DropMaterializedView(
        stable_id=f"m:{namespace}.{relname}",
        namespace=namespace,
        relname=relname,
    )

    drop_sql = generate_sql(drop_change)
    assert expected_quoted in drop_sql


def test_create_materialized_view_no_data_comment():
    """Test that materialized views are always created WITH NO DATA."""
    change = CreateMaterializedView(
        stable_id="m:public.test_view",
        namespace="public",
        relname="test_view",
        definition="SELECT id FROM users",
    )

    sql = generate_sql(change)

    # Should always include WITH NO DATA
    assert "WITH NO DATA" in sql
    # Should not include WITH DATA
    assert "WITH DATA;" not in sql


def test_replace_materialized_view_preserves_no_data():
    """Test that REPLACE operations preserve WITH NO DATA behavior."""
    change = ReplaceMaterializedView(
        stable_id="m:public.test_view",
        namespace="public",
        relname="test_view",
        definition="SELECT id, name FROM users",
    )

    sql = generate_sql(change)

    # Both statements should be present
    lines = sql.split("\n")
    assert len(lines) == 2

    # CREATE statement should have WITH NO DATA
    create_line = lines[1]
    assert "CREATE MATERIALIZED VIEW" in create_line
    assert "WITH NO DATA" in create_line
    assert create_line.endswith(";")


def test_stable_id_format():
    """Test that stable_id follows expected format for materialized views."""
    # Test different scenarios to ensure stable_id format is preserved
    cases = [
        ("public", "simple_view", "m:public.simple_view"),
        ("analytics", "complex-view", "m:analytics.complex-view"),
        ("test_schema", "view_with_underscores", "m:test_schema.view_with_underscores"),
    ]

    for namespace, relname, expected_stable_id in cases:
        change = CreateMaterializedView(
            stable_id=expected_stable_id,
            namespace=namespace,
            relname=relname,
            definition="SELECT 1",
        )

        # Verify the stable_id is preserved correctly
        assert change.stable_id == expected_stable_id
