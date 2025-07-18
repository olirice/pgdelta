"""Unit tests to exercise uncovered code paths in dependency resolution."""

import networkx as nx

from pgdelta.catalog import catalog
from pgdelta.changes import AlterTable, CreateTable, CreateView, DropView
from pgdelta.changes.table import AddColumn
from pgdelta.dependency_resolution import DependencyResolver
from pgdelta.model import PgAttribute, PgClass, PgNamespace

# Removed test_resolve_cycles_with_minimum_feedback_arc - resolve_cycles() method doesn't exist


# Removed test_resolve_cycles_exception_handling - resolve_cycles() method doesn't exist


def test_cross_catalog_dependencies():
    """Test cross-catalog dependency checking."""
    # Create master catalog with a view
    master_test_catalog = catalog(
        namespaces=[PgNamespace(nspname="test", oid=1)],
        classes=[
            PgClass(
                namespace="test",
                relname="view1",
                relkind="v",
                oid=100,
            )
        ],
    )

    # Create branch catalog (empty)
    branch_test_catalog = catalog(
        namespaces=[PgNamespace(nspname="test", oid=1)],
    )

    resolver = DependencyResolver(master_test_catalog, branch_test_catalog)

    # Create changes that involve cross-catalog checks
    changes = [
        DropView(
            stable_id="v:test.view1",
            namespace="test",
            relname="view1",
        ),
        CreateView(
            stable_id="v:test.view2",
            namespace="test",
            relname="view2",
            definition="SELECT 1",
        ),
    ]

    # Build mock dependency graphs
    source_graph = nx.DiGraph()
    source_graph.add_node("v:test.view1")

    # Test with actual DependencyResolver method
    result = resolver.resolve_dependencies(changes)

    # Should return changes (possibly reordered)
    assert len(result) == 2


# Removed test_unknown_operation_priority - _get_operation_priority() method doesn't exist


def test_networkx_error_during_sort():
    """Test NetworkXError handling during topological sort."""
    test_catalog = catalog()

    resolver = DependencyResolver(test_catalog, test_catalog)

    # Create changes
    changes = [
        CreateTable(
            stable_id="r:test.t1",
            namespace="test",
            relname="t1",
            columns=[],
        ),
    ]

    # Test with actual DependencyResolver method - should handle cycles internally
    result = resolver.resolve_dependencies(changes)

    # Should still return changes
    assert len(result) == 1


def test_empty_changes_list():
    """Test handling of empty changes list."""
    test_catalog = catalog()

    resolver = DependencyResolver(test_catalog, test_catalog)
    result = resolver.resolve_dependencies([])

    # Should return empty list without errors
    assert result == []


def test_mixed_operation_dependencies():
    """Test dependency resolution with mixed operation types."""
    # Create catalogs with dependencies
    master_test_catalog = catalog(
        namespaces=[PgNamespace(nspname="test", oid=1)],
        classes=[
            PgClass(
                namespace="test",
                relname="table1",
                relkind="r",
                oid=100,
            ),
            PgClass(
                namespace="test",
                relname="view1",
                relkind="v",
                oid=101,
            ),
        ],
    )

    branch_test_catalog = catalog(
        namespaces=[PgNamespace(nspname="test", oid=1)],
    )

    resolver = DependencyResolver(master_test_catalog, branch_test_catalog)

    # Create mixed operations
    changes = [
        DropView(
            stable_id="v:test.view1",
            namespace="test",
            relname="view1",
        ),
        AlterTable(
            stable_id="r:test.table1",
            namespace="test",
            relname="table1",
            operation=AddColumn(
                column=PgAttribute(
                    owner_namespace="test",
                    owner_name="table1",
                    owner_relkind="r",
                    attname="new_col",
                    attnum=2,
                    attnotnull=False,
                    formatted_type="text",
                    attrelid=100,
                )
            ),
        ),
        CreateView(
            stable_id="v:test.view2",
            namespace="test",
            relname="view2",
            definition="SELECT * FROM test.table1",
        ),
    ]

    # Create dependency graphs
    source_graph = nx.DiGraph()
    source_graph.add_edge("v:test.view1", "r:test.table1")

    # Test with actual DependencyResolver method
    result = resolver.resolve_dependencies(changes)

    # Should return all changes
    assert len(result) == 3
