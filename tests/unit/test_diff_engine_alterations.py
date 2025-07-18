"""Unit tests for diff engine alteration cases."""

from pgdelta.catalog import catalog
from pgdelta.diff import diff_classes, diff_schemas
from pgdelta.model import PgClass, PgNamespace


def test_schema_exists_in_both_but_changed():
    """Test when schema exists in both catalogs but has changes."""
    # Create two schemas with same name but different properties
    master_schema = PgNamespace(
        oid=16385,
        nspname="test_schema",
    )

    branch_schema = PgNamespace(
        oid=16385,
        nspname="test_schema",
    )

    master_catalog = catalog(
        namespaces=[master_schema],
    )

    branch_catalog = catalog(
        namespaces=[branch_schema],
    )

    changes = diff_schemas(master_catalog, branch_catalog)

    # Currently no ALTER SCHEMA is implemented, so no changes
    assert len(changes) == 0


def test_table_exists_in_both_but_changed():
    """Test when table exists in both catalogs but has changes."""
    # Create two tables with same name but different properties
    master_class = PgClass(
        oid=16384,
        relname="users",
        namespace="test_schema",
        relkind="r",
    )

    branch_class = PgClass(
        oid=16384,
        relname="users",
        namespace="test_schema",
        relkind="r",
    )

    master_catalog = catalog(
        classes=[master_class],
    )

    branch_catalog = catalog(
        classes=[branch_class],
    )

    changes = diff_classes(master_catalog, branch_catalog)

    # Currently no ALTER TABLE is implemented, so no changes
    assert len(changes) == 0
