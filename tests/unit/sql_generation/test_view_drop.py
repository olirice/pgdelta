"""Unit tests for DROP VIEW SQL generation."""

from pgdelta.changes.view import DropView, generate_drop_view_sql


def test_drop_view_basic():
    """Test basic DROP VIEW generation."""
    change = DropView(
        stable_id="v:public.user_summary",
        namespace="public",
        relname="user_summary",
    )

    sql = generate_drop_view_sql(change)

    assert sql == 'DROP VIEW "public"."user_summary";'


def test_drop_view_with_special_chars():
    """Test DROP VIEW with special characters in names."""
    change = DropView(
        stable_id="v:test-schema.view with spaces",
        namespace="test-schema",
        relname="view with spaces",
    )

    sql = generate_drop_view_sql(change)

    assert sql == 'DROP VIEW "test-schema"."view with spaces";'
