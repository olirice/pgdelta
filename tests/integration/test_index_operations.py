"""Integration tests for index operations.

These tests verify full end-to-end index functionality including
diff engine detection, SQL generation, and roundtrip fidelity.
"""

import pytest
from tests.integration.roundtrip import roundtrip_fidelity_test


@pytest.mark.parametrize(
    "test_name,initial_setup,test_sql,expected_terms,expected_master_dependencies,expected_branch_dependencies",
    [
        (
            "create btree index",
            """
            CREATE SCHEMA test_schema;
            CREATE TABLE test_schema.users (
                id integer,
                email character varying(255)
            );
            """,
            """
            CREATE INDEX idx_users_email ON test_schema.users (email);
            """,
            [
                "CREATE INDEX idx_users_email ON test_schema.users",
                "email",
            ],
            [
                ("r:test_schema.users", "test_schema"),  # Table depends on schema
            ],
            [
                (
                    "i:test_schema.idx_users_email",
                    "r:test_schema.users",
                ),  # Index depends on table
                ("r:test_schema.users", "test_schema"),  # Table depends on schema
            ],
        ),
        (
            "create unique index",
            """
            CREATE SCHEMA test_schema;
            CREATE TABLE test_schema.products (
                id integer,
                sku character varying(50)
            );
            """,
            """
            CREATE UNIQUE INDEX idx_products_sku ON test_schema.products (sku);
            """,
            [
                "CREATE UNIQUE INDEX idx_products_sku ON test_schema.products",
                "sku",
            ],
            [
                ("r:test_schema.products", "test_schema"),  # Table depends on schema
            ],
            [
                (
                    "i:test_schema.idx_products_sku",
                    "r:test_schema.products",
                ),  # Index depends on table
                ("r:test_schema.products", "test_schema"),  # Table depends on schema
            ],
        ),
        (
            "create partial index",
            """
            CREATE SCHEMA test_schema;
            CREATE TABLE test_schema.orders (
                id integer,
                status character varying(20),
                created_at timestamp
            );
            """,
            """
            CREATE INDEX idx_orders_pending ON test_schema.orders (created_at)
            WHERE status = 'pending';
            """,
            [
                "CREATE INDEX idx_orders_pending ON test_schema.orders",
                "created_at",
                "WHERE",
                "status",
                "pending",
            ],
            [
                ("r:test_schema.orders", "test_schema"),  # Table depends on schema
            ],
            [
                (
                    "i:test_schema.idx_orders_pending",
                    "r:test_schema.orders",
                ),  # Index depends on table
                ("r:test_schema.orders", "test_schema"),  # Table depends on schema
            ],
        ),
        (
            "create functional index",
            """
            CREATE SCHEMA test_schema;
            CREATE TABLE test_schema.customers (
                id integer,
                email character varying(255)
            );
            """,
            """
            CREATE INDEX idx_customers_email_lower ON test_schema.customers (lower(email));
            """,
            [
                "CREATE INDEX idx_customers_email_lower ON test_schema.customers",
                "lower",
                "email",
            ],
            [
                ("r:test_schema.customers", "test_schema"),  # Table depends on schema
            ],
            [
                (
                    "i:test_schema.idx_customers_email_lower",
                    "r:test_schema.customers",
                ),  # Index depends on table
                ("r:test_schema.customers", "test_schema"),  # Table depends on schema
            ],
        ),
        (
            "create multicolumn index",
            """
            CREATE SCHEMA test_schema;
            CREATE TABLE test_schema.sales (
                id integer,
                region character varying(50),
                product_id integer,
                sale_date date
            );
            """,
            """
            CREATE INDEX idx_sales_region_date ON test_schema.sales (region, sale_date);
            """,
            [
                "CREATE INDEX idx_sales_region_date ON test_schema.sales",
                "region",
                "sale_date",
            ],
            [
                ("r:test_schema.sales", "test_schema"),  # Table depends on schema
            ],
            [
                (
                    "i:test_schema.idx_sales_region_date",
                    "r:test_schema.sales",
                ),  # Index depends on table
                ("r:test_schema.sales", "test_schema"),  # Table depends on schema
            ],
        ),
        (
            "drop index",
            """
            CREATE SCHEMA test_schema;
            CREATE TABLE test_schema.items (
                id integer,
                name character varying(100)
            );
            CREATE INDEX idx_items_name ON test_schema.items (name);
            """,
            """
            DROP INDEX test_schema.idx_items_name;
            """,
            [
                'DROP INDEX "test_schema"."idx_items_name"',
            ],
            [
                (
                    "i:test_schema.idx_items_name",
                    "r:test_schema.items",
                ),  # Index depends on table (in master)
                ("r:test_schema.items", "test_schema"),  # Table depends on schema
            ],
            [
                ("r:test_schema.items", "test_schema"),  # Table depends on schema
            ],
        ),
    ],
)
@pytest.mark.integration
@pytest.mark.roundtrip
def test_index_operations(
    session,
    alt_session,
    test_name: str,
    initial_setup: str,
    test_sql: str,
    expected_terms: list[str],
    expected_master_dependencies: list[tuple[str, str]],
    expected_branch_dependencies: list[tuple[str, str]],
):
    """Test index operations with roundtrip fidelity."""
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
