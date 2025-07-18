"""Unit tests for CREATE OR REPLACE VIEW SQL generation."""

from pgdelta.changes.view import ReplaceView, generate_replace_view_sql


def test_replace_view_basic():
    """Test basic CREATE OR REPLACE VIEW generation."""
    change = ReplaceView(
        stable_id="v:public.user_summary",
        namespace="public",
        relname="user_summary",
        definition="SELECT id, name, email FROM users WHERE active = true",
    )

    sql = generate_replace_view_sql(change)

    expected = (
        'CREATE OR REPLACE VIEW "public"."user_summary" AS '
        "SELECT id, name, email FROM users WHERE active = true;"
    )
    assert sql == expected


def test_replace_view_complex_query():
    """Test CREATE OR REPLACE VIEW with complex query."""
    complex_query = """
    SELECT
        u.id,
        u.name,
        u.email,
        COUNT(o.id) as order_count,
        SUM(o.total) as total_spent
    FROM users u
    LEFT JOIN orders o ON u.id = o.user_id
    WHERE u.active = true
    GROUP BY u.id, u.name, u.email
    ORDER BY total_spent DESC
    """

    change = ReplaceView(
        stable_id="v:public.user_stats",
        namespace="public",
        relname="user_stats",
        definition=complex_query,
    )

    sql = generate_replace_view_sql(change)

    # The SQL generation should preserve the original formatting
    expected_definition = complex_query.strip()
    expected = f'CREATE OR REPLACE VIEW "public"."user_stats" AS {expected_definition};'

    assert sql == expected


def test_replace_view_with_trailing_semicolon():
    """Test that trailing semicolons are removed from definition."""
    change = ReplaceView(
        stable_id="v:public.simple_view",
        namespace="public",
        relname="simple_view",
        definition="SELECT * FROM users;",
    )

    sql = generate_replace_view_sql(change)

    assert (
        sql == 'CREATE OR REPLACE VIEW "public"."simple_view" AS SELECT * FROM users;'
    )


def test_replace_view_with_special_chars():
    """Test CREATE OR REPLACE VIEW with special characters in names."""
    change = ReplaceView(
        stable_id="v:test-schema.view with spaces",
        namespace="test-schema",
        relname="view with spaces",
        definition="SELECT 1 as col",
    )

    sql = generate_replace_view_sql(change)

    assert (
        sql
        == 'CREATE OR REPLACE VIEW "test-schema"."view with spaces" AS SELECT 1 as col;'
    )


def test_replace_view_with_subquery():
    """Test CREATE OR REPLACE VIEW with subquery."""
    subquery_definition = """
    SELECT * FROM (
        SELECT id, name,
               ROW_NUMBER() OVER (ORDER BY created_at DESC) as rn
        FROM users
    ) ranked
    WHERE rn <= 10
    """

    change = ReplaceView(
        stable_id="v:public.recent_users",
        namespace="public",
        relname="recent_users",
        definition=subquery_definition,
    )

    sql = generate_replace_view_sql(change)

    # The SQL generation should preserve the original formatting
    expected_definition = subquery_definition.strip()
    expected = (
        f'CREATE OR REPLACE VIEW "public"."recent_users" AS {expected_definition};'
    )

    assert sql == expected
