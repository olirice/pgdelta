"""Simple integration tests for materialized view operations."""

import pytest
from tests.integration.roundtrip import roundtrip_fidelity_test


@pytest.mark.integration
@pytest.mark.parametrize(
    "test_name,initial_setup,test_sql,expected_terms,expected_master_dependencies,expected_branch_dependencies",
    [
        (
            "create new materialized view",
            """
            CREATE SCHEMA test_schema;
            CREATE TABLE test_schema.users (
                id integer PRIMARY KEY,
                name text NOT NULL,
                email text,
                active boolean DEFAULT true
            );
            """,
            """
            CREATE MATERIALIZED VIEW test_schema.active_users AS
            SELECT id, name, email
            FROM test_schema.users
            WHERE active = true
            WITH NO DATA;
            """,
            ["CREATE MATERIALIZED VIEW", "WITH NO DATA"],
            [
                ("i:test_schema.users_pkey", "test_schema.users.users_pkey"),
                ("r:test_schema.users", "test_schema"),
                ("test_schema.users.users_pkey", "r:test_schema.users"),
            ],
            [
                ("i:test_schema.users_pkey", "test_schema.users.users_pkey"),
                ("r:test_schema.users", "test_schema"),
                ("test_schema.users.users_pkey", "r:test_schema.users"),
                ("m:test_schema.active_users", "test_schema"),
                ("m:test_schema.active_users", "r:test_schema.users"),
            ],
        ),
        (
            "drop existing materialized view",
            """
            CREATE SCHEMA test_schema;
            CREATE TABLE test_schema.users (
                id integer PRIMARY KEY,
                name text NOT NULL,
                active boolean DEFAULT true
            );

            CREATE MATERIALIZED VIEW test_schema.active_users AS
            SELECT id, name
            FROM test_schema.users
            WHERE active = true
            WITH NO DATA;
            """,
            """
            DROP MATERIALIZED VIEW test_schema.active_users;
            """,
            ["DROP MATERIALIZED VIEW"],
            [
                ("i:test_schema.users_pkey", "test_schema.users.users_pkey"),
                ("r:test_schema.users", "test_schema"),
                ("test_schema.users.users_pkey", "r:test_schema.users"),
                ("m:test_schema.active_users", "test_schema"),
                ("m:test_schema.active_users", "r:test_schema.users"),
            ],
            [
                ("i:test_schema.users_pkey", "test_schema.users.users_pkey"),
                ("r:test_schema.users", "test_schema"),
                ("test_schema.users.users_pkey", "r:test_schema.users"),
            ],
        ),
        (
            "replace materialized view definition",
            """
            CREATE SCHEMA test_schema;
            CREATE TABLE test_schema.users (
                id integer PRIMARY KEY,
                name text NOT NULL,
                email text,
                active boolean DEFAULT true
            );

            CREATE MATERIALIZED VIEW test_schema.user_summary AS
            SELECT id, name
            FROM test_schema.users
            WHERE active = true
            WITH NO DATA;
            """,
            """
            DROP MATERIALIZED VIEW test_schema.user_summary;
            CREATE MATERIALIZED VIEW test_schema.user_summary AS
            SELECT id, name, email
            FROM test_schema.users
            WHERE active = true
            ORDER BY name
            WITH NO DATA;
            """,
            ["DROP MATERIALIZED VIEW", "CREATE MATERIALIZED VIEW", "ORDER BY name"],
            [
                ("i:test_schema.users_pkey", "test_schema.users.users_pkey"),
                ("r:test_schema.users", "test_schema"),
                ("test_schema.users.users_pkey", "r:test_schema.users"),
                ("m:test_schema.user_summary", "test_schema"),
                ("m:test_schema.user_summary", "r:test_schema.users"),
            ],
            [
                ("i:test_schema.users_pkey", "test_schema.users.users_pkey"),
                ("r:test_schema.users", "test_schema"),
                ("test_schema.users.users_pkey", "r:test_schema.users"),
                ("m:test_schema.user_summary", "test_schema"),
                ("m:test_schema.user_summary", "r:test_schema.users"),
            ],
        ),
    ],
)
def test_materialized_view_operations(
    session,
    alt_session,
    test_name,
    initial_setup,
    test_sql,
    expected_terms,
    expected_master_dependencies,
    expected_branch_dependencies,
):
    """Test materialized view operations using roundtrip fidelity validation."""
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


@pytest.mark.integration
def test_materialized_view_with_aggregations(session, alt_session):
    """Test materialized view with complex aggregations."""
    roundtrip_fidelity_test(
        master_session=session,
        branch_session=alt_session,
        initial_setup="""
            CREATE SCHEMA analytics;
            CREATE TABLE analytics.sales (
                id integer PRIMARY KEY,
                customer_id integer,
                amount decimal(10,2),
                sale_date date
            );
        """,
        test_sql="""
            CREATE MATERIALIZED VIEW analytics.monthly_sales AS
            SELECT
                DATE_TRUNC('month', sale_date) as month,
                COUNT(*) as total_sales,
                SUM(amount) as total_revenue
            FROM analytics.sales
            GROUP BY DATE_TRUNC('month', sale_date)
            ORDER BY month
            WITH NO DATA;
        """,
        description="materialized view with aggregations",
        expected_sql_terms=[
            "CREATE MATERIALIZED VIEW",
            "date_trunc",
            "GROUP BY",
            "WITH NO DATA",
        ],
        expected_master_dependencies=[
            ("i:analytics.sales_pkey", "analytics.sales.sales_pkey"),
            ("r:analytics.sales", "analytics"),
            ("analytics.sales.sales_pkey", "r:analytics.sales"),
        ],
        expected_branch_dependencies=[
            ("i:analytics.sales_pkey", "analytics.sales.sales_pkey"),
            ("r:analytics.sales", "analytics"),
            ("analytics.sales.sales_pkey", "r:analytics.sales"),
            ("m:analytics.monthly_sales", "analytics"),
            ("m:analytics.monthly_sales", "r:analytics.sales"),
        ],
    )


@pytest.mark.integration
def test_materialized_view_with_joins(session, alt_session):
    """Test materialized view with JOINs."""
    roundtrip_fidelity_test(
        master_session=session,
        branch_session=alt_session,
        initial_setup="""
            CREATE SCHEMA ecommerce;
            CREATE TABLE ecommerce.customers (
                id integer PRIMARY KEY,
                name text NOT NULL
            );

            CREATE TABLE ecommerce.orders (
                id integer PRIMARY KEY,
                customer_id integer,
                total decimal(10,2)
            );
        """,
        test_sql="""
            CREATE MATERIALIZED VIEW ecommerce.customer_orders AS
            SELECT
                c.id as customer_id,
                c.name,
                COUNT(o.id) as order_count,
                COALESCE(SUM(o.total), 0) as total_spent
            FROM ecommerce.customers c
            LEFT JOIN ecommerce.orders o ON c.id = o.customer_id
            GROUP BY c.id, c.name
            WITH NO DATA;
        """,
        description="materialized view with joins",
        expected_sql_terms=[
            "CREATE MATERIALIZED VIEW",
            "LEFT JOIN",
            "COALESCE",
            "WITH NO DATA",
        ],
        expected_master_dependencies=[
            ("i:ecommerce.customers_pkey", "ecommerce.customers.customers_pkey"),
            ("i:ecommerce.orders_pkey", "ecommerce.orders.orders_pkey"),
            ("r:ecommerce.customers", "ecommerce"),
            ("r:ecommerce.orders", "ecommerce"),
            ("ecommerce.customers.customers_pkey", "r:ecommerce.customers"),
            ("ecommerce.orders.orders_pkey", "r:ecommerce.orders"),
        ],
        expected_branch_dependencies=[
            ("i:ecommerce.customers_pkey", "ecommerce.customers.customers_pkey"),
            ("i:ecommerce.orders_pkey", "ecommerce.orders.orders_pkey"),
            ("r:ecommerce.customers", "ecommerce"),
            ("r:ecommerce.orders", "ecommerce"),
            ("ecommerce.customers.customers_pkey", "r:ecommerce.customers"),
            ("ecommerce.orders.orders_pkey", "r:ecommerce.orders"),
            ("m:ecommerce.customer_orders", "ecommerce"),
            ("m:ecommerce.customer_orders", "r:ecommerce.customers"),
            ("m:ecommerce.customer_orders", "r:ecommerce.orders"),
        ],
    )
