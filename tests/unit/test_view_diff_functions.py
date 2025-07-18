"""Unit tests for view diff functions."""

from pgdelta.catalog import catalog
from pgdelta.changes.view import CreateView, DropView, ReplaceView
from pgdelta.diff import diff_classes
from pgdelta.model import PgClass


def test_create_view():
    """Test creating a new view."""
    master_catalog = catalog()

    branch_view = PgClass(
        namespace="public",
        relname="user_summary",
        relkind="v",
        oid=16384,
        view_definition="SELECT id, name FROM users",
    )

    branch_catalog = catalog(
        classes=[branch_view],
    )

    changes = diff_classes(master_catalog, branch_catalog)

    assert len(changes) == 1
    assert isinstance(changes[0], CreateView)
    assert changes[0].relname == "user_summary"
    assert changes[0].namespace == "public"
    assert changes[0].definition == "SELECT id, name FROM users"


def test_drop_view():
    """Test dropping an existing view."""
    master_view = PgClass(
        namespace="public",
        relname="old_view",
        relkind="v",
        oid=16384,
        view_definition="SELECT * FROM old_table",
    )

    master_catalog = catalog(
        classes=[master_view],
    )

    branch_catalog = catalog()

    changes = diff_classes(master_catalog, branch_catalog)

    assert len(changes) == 1
    assert isinstance(changes[0], DropView)
    assert changes[0].relname == "old_view"
    assert changes[0].namespace == "public"


def test_replace_view_different_definition():
    """Test replacing a view with different definition."""
    master_view = PgClass(
        namespace="public",
        relname="user_summary",
        relkind="v",
        oid=16384,
        view_definition="SELECT id, name FROM users",
    )

    branch_view = PgClass(
        namespace="public",
        relname="user_summary",
        relkind="v",
        oid=16384,
        view_definition="SELECT id, name, email FROM users WHERE active = true",
    )

    master_catalog = catalog(
        classes=[master_view],
    )

    branch_catalog = catalog(
        classes=[branch_view],
    )

    changes = diff_classes(master_catalog, branch_catalog)

    assert len(changes) == 1
    assert isinstance(changes[0], ReplaceView)
    assert changes[0].relname == "user_summary"
    assert changes[0].namespace == "public"
    assert (
        changes[0].definition == "SELECT id, name, email FROM users WHERE active = true"
    )


def test_view_unchanged():
    """Test view with same definition produces no changes."""
    definition = "SELECT id, name FROM users"

    view = PgClass(
        namespace="public",
        relname="user_summary",
        relkind="v",
        oid=16384,
        view_definition=definition,
    )

    master_catalog = catalog(
        classes=[view],
    )

    branch_catalog = catalog(
        classes=[view],
    )

    changes = diff_classes(master_catalog, branch_catalog)

    assert len(changes) == 0


def test_view_definition_whitespace_normalization():
    """Test that whitespace differences in view definitions are normalized."""
    source_definition = "SELECT   id,    name   FROM users"
    target_definition = "SELECT id, name FROM users"

    master_view = PgClass(
        namespace="public",
        relname="user_summary",
        relkind="v",
        oid=16384,
        view_definition=source_definition,
    )

    branch_view = PgClass(
        namespace="public",
        relname="user_summary",
        relkind="v",
        oid=16384,
        view_definition=target_definition,
    )

    master_catalog = catalog(
        classes=[master_view],
    )

    branch_catalog = catalog(
        classes=[branch_view],
    )

    changes = diff_classes(master_catalog, branch_catalog)

    # Should have no changes because definitions are equivalent after normalization
    assert len(changes) == 0


def test_ignore_non_views():
    """Test that non-view relations are still ignored in view diff functions."""
    source_table = PgClass(
        namespace="public",
        relname="test_table",
        relkind="r",  # table, not view
        oid=16384,
    )

    master_catalog = catalog(
        classes=[source_table],
    )

    branch_catalog = catalog()

    changes = diff_classes(master_catalog, branch_catalog)

    # Should handle table drops, not view drops
    assert len(changes) == 1
    # Should be DropTable, not DropView
    assert "DropTable" in str(type(changes[0]))


def test_mixed_views_and_tables():
    """Test handling both view and table changes in same diff."""
    # Source has table and view
    source_table = PgClass(namespace="public", relname="users", relkind="r", oid=16384)
    master_view = PgClass(
        namespace="public",
        relname="user_summary",
        relkind="v",
        oid=16385,
        view_definition="SELECT * FROM users",
    )

    # Target has only table (view dropped) and new view
    target_table = PgClass(namespace="public", relname="users", relkind="r", oid=16384)
    branch_view = PgClass(
        namespace="public",
        relname="active_users",
        relkind="v",
        oid=16386,
        view_definition="SELECT * FROM users WHERE active = true",
    )

    master_catalog = catalog(
        classes=[source_table, master_view],
    )

    branch_catalog = catalog(
        classes=[target_table, branch_view],
    )

    changes = diff_classes(master_catalog, branch_catalog)

    # Should have 2 changes: drop old view, create new view
    assert len(changes) == 2

    change_types = [type(change).__name__ for change in changes]
    assert "DropView" in change_types
    assert "CreateView" in change_types
