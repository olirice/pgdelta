"""Integration tests for view operations and dependencies."""

import pytest
from tests.integration.roundtrip import roundtrip_fidelity_test


@pytest.mark.parametrize(
    "test_name,initial_setup,test_sql,expected_terms,expected_master_dependencies,expected_branch_dependencies",
    [
        (
            "simple view creation",
            "CREATE SCHEMA test_schema",
            """
            CREATE TABLE test_schema.users (
                id integer,
                name text,
                email text
            );

            CREATE VIEW test_schema.active_users AS
            SELECT id, name, email
            FROM test_schema.users
            WHERE email IS NOT NULL;
            """,
            [
                'CREATE TABLE "test_schema"."users"',
                'CREATE VIEW "test_schema"."active_users"',
                "SELECT id",
                "FROM test_schema.users",
                "WHERE (email IS NOT NULL)",
            ],
            [],  # Master has no dependencies (empty state)
            [
                ("r:test_schema.users", "test_schema"),
                ("v:test_schema.active_users", "test_schema"),
                ("v:test_schema.active_users", "r:test_schema.users"),
            ],
        ),
        (
            "nested view dependencies - 3 levels deep",
            "CREATE SCHEMA test_schema",
            """
            CREATE TABLE test_schema.users (
                id integer,
                name text,
                email text,
                created_at timestamp DEFAULT NOW()
            );

            CREATE TABLE test_schema.orders (
                id integer,
                user_id integer,
                amount decimal(10,2),
                created_at timestamp DEFAULT NOW()
            );

            -- Level 1: Views directly on tables
            CREATE VIEW test_schema.recent_users AS
            SELECT id, name, email, created_at
            FROM test_schema.users
            WHERE created_at > NOW() - INTERVAL '30 days';

            CREATE VIEW test_schema.high_value_orders AS
            SELECT id, user_id, amount, created_at
            FROM test_schema.orders
            WHERE amount > 100;

            -- Level 2: Views on other views
            CREATE VIEW test_schema.recent_big_spenders AS
            SELECT u.id, u.name, u.email, COUNT(o.id) as order_count, SUM(o.amount) as total_spent
            FROM test_schema.recent_users u
            JOIN test_schema.high_value_orders o ON u.id = o.user_id
            GROUP BY u.id, u.name, u.email;

            -- Level 3: Views on views of views
            CREATE VIEW test_schema.top_customers AS
            SELECT id, name, email, total_spent
            FROM test_schema.recent_big_spenders
            WHERE total_spent > 1000
            ORDER BY total_spent DESC
            LIMIT 10;
            """,
            [
                'CREATE TABLE "test_schema"."users"',
                'CREATE TABLE "test_schema"."orders"',
                'CREATE VIEW "test_schema"."recent_users"',
                'CREATE VIEW "test_schema"."high_value_orders"',
                'CREATE VIEW "test_schema"."recent_big_spenders"',
                'CREATE VIEW "test_schema"."top_customers"',
            ],
            [],  # Master has no dependencies (empty state)
            [
                # Table-schema dependencies
                ("r:test_schema.users", "test_schema"),
                ("r:test_schema.orders", "test_schema"),
                # View-schema dependencies
                ("v:test_schema.recent_users", "test_schema"),
                ("v:test_schema.high_value_orders", "test_schema"),
                ("v:test_schema.recent_big_spenders", "test_schema"),
                ("v:test_schema.top_customers", "test_schema"),
                # Level 1 view-table dependencies
                ("v:test_schema.recent_users", "r:test_schema.users"),
                ("v:test_schema.high_value_orders", "r:test_schema.orders"),
                # Level 2 view-view dependencies
                ("v:test_schema.recent_big_spenders", "v:test_schema.recent_users"),
                (
                    "v:test_schema.recent_big_spenders",
                    "v:test_schema.high_value_orders",
                ),
                # Level 3 view-view dependencies
                ("v:test_schema.top_customers", "v:test_schema.recent_big_spenders"),
            ],
        ),
        (
            "view replacement with dependency changes",
            """
            CREATE SCHEMA test_schema;

            CREATE TABLE test_schema.users (
                id integer,
                name text,
                status text
            );

            CREATE TABLE test_schema.profiles (
                user_id integer,
                bio text,
                avatar_url text
            );

            CREATE VIEW test_schema.user_summary AS
            SELECT id, name, status
            FROM test_schema.users;
            """,
            """
            -- Replace view to include profile data (new dependency)
            CREATE OR REPLACE VIEW test_schema.user_summary AS
            SELECT u.id, u.name, u.status, p.bio, p.avatar_url
            FROM test_schema.users u
            LEFT JOIN test_schema.profiles p ON u.id = p.user_id;
            """,
            [
                'CREATE OR REPLACE VIEW "test_schema"."user_summary"',
                "SELECT u.id,",
                "u.name,",
                "u.status,",
                "p.bio,",
                "p.avatar_url",
                "LEFT JOIN test_schema.profiles p",
            ],
            [
                ("r:test_schema.users", "test_schema"),
                ("r:test_schema.profiles", "test_schema"),
                ("v:test_schema.user_summary", "test_schema"),
                ("v:test_schema.user_summary", "r:test_schema.users"),
            ],  # Master has view depending only on users table
            [
                ("r:test_schema.users", "test_schema"),
                ("r:test_schema.profiles", "test_schema"),
                ("v:test_schema.user_summary", "test_schema"),
                ("v:test_schema.user_summary", "r:test_schema.users"),
                ("v:test_schema.user_summary", "r:test_schema.profiles"),
            ],  # Branch has view depending on both tables
        ),
        (
            "complex view dependencies with multiple joins",
            "CREATE SCHEMA analytics",
            """
            CREATE TABLE analytics.customers (
                id integer,
                name text,
                region text,
                tier text
            );

            CREATE TABLE analytics.products (
                id integer,
                name text,
                category text,
                price decimal(10,2)
            );

            CREATE TABLE analytics.sales (
                id integer,
                customer_id integer,
                product_id integer,
                quantity integer,
                sale_date date
            );

            -- Base analytical views
            CREATE VIEW analytics.customer_stats AS
            SELECT
                c.id,
                c.name,
                c.region,
                c.tier,
                COUNT(s.id) as total_orders,
                SUM(s.quantity * p.price) as total_revenue
            FROM analytics.customers c
            LEFT JOIN analytics.sales s ON c.id = s.customer_id
            LEFT JOIN analytics.products p ON s.product_id = p.id
            GROUP BY c.id, c.name, c.region, c.tier;

            CREATE VIEW analytics.product_performance AS
            SELECT
                p.id,
                p.name,
                p.category,
                p.price,
                COUNT(s.id) as units_sold,
                SUM(s.quantity) as total_quantity
            FROM analytics.products p
            LEFT JOIN analytics.sales s ON p.id = s.product_id
            GROUP BY p.id, p.name, p.category, p.price;

            -- Higher-level analytics view depending on both above views
            CREATE VIEW analytics.business_summary AS
            SELECT
                'customers' as metric_type,
                COUNT(*) as count,
                AVG(total_revenue) as avg_value
            FROM analytics.customer_stats
            WHERE total_revenue > 0

            UNION ALL

            SELECT
                'products' as metric_type,
                COUNT(*) as count,
                AVG(price) as avg_value
            FROM analytics.product_performance
            WHERE units_sold > 0;
            """,
            [
                'CREATE TABLE "analytics"."customers"',
                'CREATE TABLE "analytics"."products"',
                'CREATE TABLE "analytics"."sales"',
                'CREATE VIEW "analytics"."customer_stats"',
                'CREATE VIEW "analytics"."product_performance"',
                'CREATE VIEW "analytics"."business_summary"',
                "UNION ALL",
            ],
            [],  # Master has no dependencies (empty state)
            [
                # Table dependencies
                ("r:analytics.customers", "analytics"),
                ("r:analytics.products", "analytics"),
                ("r:analytics.sales", "analytics"),
                # View dependencies
                ("v:analytics.customer_stats", "analytics"),
                ("v:analytics.product_performance", "analytics"),
                ("v:analytics.business_summary", "analytics"),
                # View-table dependencies
                ("v:analytics.customer_stats", "r:analytics.customers"),
                ("v:analytics.customer_stats", "r:analytics.sales"),
                ("v:analytics.customer_stats", "r:analytics.products"),
                ("v:analytics.product_performance", "r:analytics.products"),
                ("v:analytics.product_performance", "r:analytics.sales"),
                # View-view dependencies
                ("v:analytics.business_summary", "v:analytics.customer_stats"),
                ("v:analytics.business_summary", "v:analytics.product_performance"),
            ],
        ),
    ],
)
@pytest.mark.integration
def test_view_operations(
    session,
    alt_session,
    test_name,
    initial_setup,
    test_sql,
    expected_terms,
    expected_master_dependencies,
    expected_branch_dependencies,
):
    """Test view operations using roundtrip fidelity validation."""
    roundtrip_fidelity_test(
        master_session=session,
        branch_session=alt_session,
        initial_setup=initial_setup,
        test_sql=test_sql,
        description=test_name,
        expected_sql_terms=expected_terms,
        expected_master_dependencies=expected_master_dependencies,
        expected_branch_dependencies=expected_branch_dependencies,
    )


# CASCADE operations are intentionally not supported as dependency resolution
# handles proper ordering of DROP operations automatically


# NOTE: View cycles can occur in PostgreSQL through recursive CTEs or complex dependency patterns.
# For example:
# - View A references View B in a subquery
# - View B references View A in a different context
# - Both views exist but create a logical circular dependency
#
# PostgreSQL itself prevents direct cycles during view creation, but complex patterns
# involving multiple views, functions, and recursive CTEs can create scenarios where
# dependency resolution becomes challenging.
#
# TODO: Add integration tests for view cycle detection once cycle detection is implemented
# in the dependency resolution system. These tests should verify that:
# 1. Obvious cycles are detected and reported
# 2. Complex multi-level cycles are identified
# 3. False positives (valid recursive patterns) are not flagged as cycles
# 4. Proper error messages guide users on how to resolve cycles
