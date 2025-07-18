"""Test view dependencies extraction from pg_rewrite."""

import pytest
from sqlalchemy import text

from pgdelta.catalog import extract_catalog
from pgdelta.model.pg_class import extract_classes
from pgdelta.model.pg_depend import (
    extract_view_dependencies_as_pg_depend,
)


@pytest.mark.integration
def test_view_dependencies_from_pg_rewrite(session):
    """Test that view dependencies are correctly extracted from pg_rewrite."""
    # Create test schema and base table
    session.execute(
        text("""
            CREATE SCHEMA test_schema;

            CREATE TABLE test_schema.users (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT,
                active BOOLEAN DEFAULT true
            );

            CREATE TABLE test_schema.orders (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES test_schema.users(id),
                amount DECIMAL(10,2),
                created_at TIMESTAMP DEFAULT NOW()
            );
        """)
    )

    # Create views with dependencies
    session.execute(
        text("""
            -- Simple view depending on users table
            CREATE VIEW test_schema.active_users AS
            SELECT id, name, email
            FROM test_schema.users
            WHERE active = true;

            -- View depending on multiple tables
            CREATE VIEW test_schema.user_orders AS
            SELECT u.name, u.email, o.amount, o.created_at
            FROM test_schema.users u
            JOIN test_schema.orders o ON u.id = o.user_id;

            -- Nested view depending on another view
            CREATE VIEW test_schema.active_user_orders AS
            SELECT au.name, au.email, o.amount, o.created_at
            FROM test_schema.active_users au
            JOIN test_schema.orders o ON au.id = o.user_id;
        """)
    )

    session.commit()

    # Extract catalog data
    classes = extract_classes(session)

    # Extract view dependencies
    view_deps = extract_view_dependencies_as_pg_depend(session, classes)

    # Verify we have view dependencies
    assert len(view_deps) > 0, "Should have extracted view dependencies"

    # Check that all returned objects are PgDepend instances
    from pgdelta.model.pg_depend import PgDepend

    for dep in view_deps:
        assert isinstance(dep, PgDepend), "Should return PgDepend objects"

    # Find dependencies by stable_id
    dep_map = {}
    for dep in view_deps:
        if dep.dependent_stable_id not in dep_map:
            dep_map[dep.dependent_stable_id] = []
        dep_map[dep.dependent_stable_id].append(dep.referenced_stable_id)

    # Verify expected dependencies
    # active_users view should depend on users table
    active_users_deps = dep_map.get("v:test_schema.active_users", [])
    assert "r:test_schema.users" in active_users_deps, (
        "active_users view should depend on users table"
    )

    # user_orders view should depend on both users and orders tables
    user_orders_deps = dep_map.get("v:test_schema.user_orders", [])
    assert "r:test_schema.users" in user_orders_deps, (
        "user_orders view should depend on users table"
    )
    assert "r:test_schema.orders" in user_orders_deps, (
        "user_orders view should depend on orders table"
    )

    # active_user_orders view should depend on active_users view and orders table
    active_user_orders_deps = dep_map.get("v:test_schema.active_user_orders", [])
    assert "v:test_schema.active_users" in active_user_orders_deps, (
        "active_user_orders view should depend on active_users view"
    )
    assert "r:test_schema.orders" in active_user_orders_deps, (
        "active_user_orders view should depend on orders table"
    )

    # Verify dependency properties
    for dep in view_deps:
        assert dep.deptype == "n", "View dependencies should be normal dependencies"
        assert dep.objsubid == 0, (
            "View dependencies should be whole-object dependencies"
        )
        assert dep.classid_name == "pg_class", "View should be in pg_class"
        assert dep.dependent_stable_id.startswith("v:"), "Dependent should be a view"
        assert dep.referenced_stable_id.startswith(("r:", "v:")), (
            "Referenced should be table or view"
        )


@pytest.mark.integration
def test_view_dependencies_in_full_catalog_extraction(session):
    """Test that view dependencies are included in full catalog extraction."""
    # Create test schema with view dependencies
    session.execute(
        text("""
            CREATE SCHEMA test_schema;

            CREATE TABLE test_schema.base_table (
                id SERIAL PRIMARY KEY,
                data TEXT
            );

            CREATE VIEW test_schema.base_view AS
            SELECT id, upper(data) as upper_data
            FROM test_schema.base_table;
        """)
    )

    session.commit()

    # Extract full catalog
    catalog = extract_catalog(session)

    # Verify view dependencies are included in catalog dependencies
    view_deps = [
        dep for dep in catalog.depends if dep.dependent_stable_id.startswith("v:")
    ]

    assert len(view_deps) > 0, "Catalog should include view dependencies"

    # Find the specific dependency we expect
    base_view_deps = [
        dep
        for dep in view_deps
        if dep.dependent_stable_id == "v:test_schema.base_view"
        and dep.referenced_stable_id == "r:test_schema.base_table"
    ]

    assert len(base_view_deps) >= 1, (
        "Should have at least one dependency from base_view to base_table"
    )

    # Verify all dependencies are normal dependencies
    for dep in base_view_deps:
        assert dep.deptype == "n", "Should be normal dependency"
        assert dep.objsubid == 0, "Should be whole-object dependency"


@pytest.mark.integration
def test_no_view_dependencies_when_no_views(session):
    """Test that no view dependencies are extracted when there are no views."""
    # Create test schema with only tables, no views
    session.execute(
        text("""
            CREATE SCHEMA test_schema;

            CREATE TABLE test_schema.table1 (
                id SERIAL PRIMARY KEY,
                data TEXT
            );

            CREATE TABLE test_schema.table2 (
                id SERIAL PRIMARY KEY,
                ref_id INTEGER REFERENCES test_schema.table1(id)
            );
        """)
    )

    session.commit()

    # Extract catalog data
    classes = extract_classes(session)

    # Extract view dependencies
    view_deps = extract_view_dependencies_as_pg_depend(session, classes)

    # Should be empty since there are no views
    assert len(view_deps) == 0, (
        "Should have no view dependencies when there are no views"
    )
