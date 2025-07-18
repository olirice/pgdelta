"""Minimal tests to reach 95% coverage."""

from pgdelta.catalog import catalog
from pgdelta.changes.table import AlterTable
from pgdelta.dependency_resolution import DependencyResolver
from pgdelta.model import PgNamespace

# Removed test_resolve_cycles_no_cycles - resolve_cycles() method doesn't exist


# Removed test_resolve_cycles_with_cycles - resolve_cycles() method doesn't exist


# Removed test_resolve_cycles_networkx_exception - resolve_cycles() method doesn't exist


def test_catalog_semantic_equality_edge_cases():
    """Test semantic equality edge cases in catalog."""
    namespace1 = PgNamespace(oid=123, nspname="schema1")
    namespace2 = PgNamespace(oid=124, nspname="schema2")

    # Different schema counts
    test_catalog1 = catalog(
        namespaces=[namespace1],
    )
    test_catalog2 = catalog(
        namespaces=[namespace1, namespace2],
    )
    assert not test_catalog1.semantically_equals(test_catalog2)

    # Different schema names
    test_catalog3 = catalog(
        namespaces=[namespace1],
    )
    test_catalog4 = catalog(
        namespaces=[namespace2],
    )
    assert not test_catalog3.semantically_equals(test_catalog4)


def test_resolve_dependencies_empty_list():
    """Test resolve_dependencies with empty changes list."""
    test_catalog = catalog()
    resolver = DependencyResolver(test_catalog, test_catalog)

    # Test with empty list - should return early (line 118)
    result = resolver.resolve_dependencies([])
    assert result == []


def test_resolve_dependencies_with_alter_operations():
    """Test resolve_dependencies with ALTER operations to trigger lines 150-153."""
    test_catalog = catalog()
    resolver = DependencyResolver(test_catalog, test_catalog)

    # Create a mock AlterTable change to trigger ALTER handling
    from pgdelta.changes.table import AddColumn
    from pgdelta.model import PgAttribute

    mock_column = PgAttribute(
        owner_namespace="public",
        owner_name="test_table",
        owner_relkind="r",
        attname="test_col",
        attnum=1,
        attnotnull=False,
        formatted_type="text",
        attrelid=16384,
    )

    alter_change = AlterTable(
        stable_id="r:public.test_table",
        namespace="public",
        relname="test_table",
        operation=AddColumn(column=mock_column),
    )

    # This should trigger the ALTER handling path (lines 150-153)
    result = resolver.resolve_dependencies([alter_change])
    assert len(result) == 1
    assert result[0] == alter_change
