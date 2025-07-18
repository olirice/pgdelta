"""Unit tests for diff functions."""

from pgdelta.catalog import catalog
from pgdelta.changes.schema import CreateSchema, DropSchema
from pgdelta.changes.table import CreateTable, DropTable
from pgdelta.changes.view import CreateView, DropView
from pgdelta.diff import diff_catalogs, diff_classes, diff_schemas
from pgdelta.model import PgAttribute, PgClass, PgNamespace


def test_diff_empty_catalogs():
    """Test diff between two empty catalogs."""
    empty_catalog = catalog()

    changes = diff_catalogs(empty_catalog, empty_catalog)

    assert changes == []


def test_create_schema():
    """Test creating a new schema."""
    master_catalog = catalog()

    branch_namespace = PgNamespace(
        nspname="new_schema",
        oid=12345,
    )

    branch_catalog = catalog(
        namespaces=[branch_namespace],
    )

    changes = diff_schemas(master_catalog, branch_catalog)

    assert len(changes) == 1
    assert isinstance(changes[0], CreateSchema)
    assert changes[0].nspname == "new_schema"
    assert changes[0].stable_id == "new_schema"


def test_drop_schema():
    """Test dropping an existing schema."""
    master_namespace = PgNamespace(
        nspname="old_schema",
        oid=12345,
    )

    master_catalog = catalog(
        namespaces=[master_namespace],
    )

    branch_catalog = catalog()

    changes = diff_schemas(master_catalog, branch_catalog)

    assert len(changes) == 1
    assert isinstance(changes[0], DropSchema)
    assert changes[0].nspname == "old_schema"
    assert changes[0].stable_id == "old_schema"


def test_unchanged_schema():
    """Test schema that exists in both catalogs unchanged."""
    namespace = PgNamespace(
        nspname="unchanged_schema",
        oid=12345,
    )

    master_catalog = catalog(
        namespaces=[namespace],
    )

    branch_catalog = catalog(
        namespaces=[namespace],
    )

    changes = diff_schemas(master_catalog, branch_catalog)

    assert changes == []


def test_create_table():
    """Test creating a new table."""
    master_catalog = catalog()

    branch_class = PgClass(
        namespace="public",
        relname="users",
        relkind="r",
        oid=16384,
    )

    branch_column = PgAttribute(
        owner_namespace="public",
        owner_name="users",
        owner_relkind="r",
        attname="id",
        attnum=1,
        attnotnull=True,
        formatted_type="integer",
        attrelid=16384,
    )

    branch_catalog = catalog(
        classes=[branch_class],
        attributes=[branch_column],
    )

    changes = diff_classes(master_catalog, branch_catalog)

    assert len(changes) == 1
    assert isinstance(changes[0], CreateTable)
    assert changes[0].relname == "users"
    assert changes[0].namespace == "public"
    assert len(changes[0].columns) == 1
    assert changes[0].columns[0].attname == "id"


def test_drop_table():
    """Test dropping an existing table."""
    source_class = PgClass(
        namespace="public",
        relname="old_table",
        relkind="r",
        oid=16384,
    )

    master_catalog = catalog(
        classes=[source_class],
    )

    branch_catalog = catalog()

    changes = diff_classes(master_catalog, branch_catalog)

    assert len(changes) == 1
    assert isinstance(changes[0], DropTable)
    assert changes[0].relname == "old_table"
    assert changes[0].namespace == "public"


def test_process_views():
    """Test that views are now processed and generate appropriate changes."""
    source_view = PgClass(
        namespace="public",
        relname="test_view",
        relkind="v",  # View
        oid=16384,
        view_definition="SELECT 1",
    )

    master_catalog = catalog(
        classes=[source_view],
    )

    branch_catalog = catalog()

    changes = diff_classes(master_catalog, branch_catalog)

    # Should generate DropView change
    assert len(changes) == 1
    assert isinstance(changes[0], DropView)
    assert changes[0].relname == "test_view"
    assert changes[0].namespace == "public"


def test_process_views_in_target():
    """Test that views in target are now processed and generate appropriate changes."""
    target_view = PgClass(
        namespace="public",
        relname="test_view",
        relkind="v",  # View, not table
        oid=16384,
        view_definition="SELECT 1",
    )

    master_catalog = catalog()

    branch_catalog = catalog(
        classes=[target_view],
    )

    changes = diff_classes(master_catalog, branch_catalog)

    # Should generate CreateView change (new view creation)
    assert len(changes) == 1
    assert isinstance(changes[0], CreateView)
    assert changes[0].relname == "test_view"
    assert changes[0].namespace == "public"
