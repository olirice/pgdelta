"""Integration tests for mixed database objects (schemas + tables)."""

import pytest
from tests.integration.roundtrip import roundtrip_fidelity_test


@pytest.mark.parametrize(
    "initial_setup,test_sql,description,expected_sql_terms,expected_master_dependencies,expected_branch_dependencies",
    [
        # Schema and table creation
        (
            None,
            """
            CREATE SCHEMA test_schema;
            CREATE TABLE test_schema.users (
                id integer,
                name text NOT NULL,
                email text,
                created_at timestamp DEFAULT now()
            );
            """,
            "schema and table creation",
            [
                'CREATE SCHEMA "test_schema"',
                'CREATE TABLE "test_schema"."users"',
                '"id" integer',
                '"name" text NOT NULL',
                '"email" text',
                '"created_at" timestamp without time zone',
            ],
            [],  # Master has no dependencies (empty state)
            [
                ("r:test_schema.users", "test_schema"),
            ],
        ),
        # Multiple schemas and tables
        (
            None,
            """
            CREATE SCHEMA core;
            CREATE SCHEMA analytics;

            CREATE TABLE core.users (
                id integer,
                username text NOT NULL,
                email text
            );

            CREATE TABLE core.posts (
                id integer,
                title text NOT NULL,
                content text,
                user_id integer
            );

            CREATE TABLE analytics.user_stats (
                user_id integer,
                post_count integer DEFAULT 0,
                last_login timestamp
            );
            """,
            "multiple schemas and tables",
            [
                'CREATE SCHEMA "core"',
                'CREATE SCHEMA "analytics"',
                'CREATE TABLE "core"."users"',
                'CREATE TABLE "core"."posts"',
                'CREATE TABLE "analytics"."user_stats"',
                '"username" text NOT NULL',
                '"title" text NOT NULL',
                '"post_count" integer',
            ],
            [],  # Master has no dependencies (empty state)
            [
                ("r:core.users", "core"),
                ("r:core.posts", "core"),
                ("r:analytics.user_stats", "analytics"),
            ],
        ),
        # Complex column types
        (
            None,
            """
            CREATE SCHEMA test_schema;
            CREATE TABLE test_schema.complex_table (
                id uuid,
                metadata jsonb,
                tags text[],
                coordinates point,
                price numeric(10,2),
                is_active boolean DEFAULT true,
                created_at timestamptz DEFAULT now()
            );
            """,
            "complex column types",
            [
                'CREATE SCHEMA "test_schema"',
                'CREATE TABLE "test_schema"."complex_table"',
                '"id" uuid',
                '"metadata" jsonb',
                '"tags" text[]',
                '"coordinates" point',
                '"price" numeric(10,2)',
                '"is_active" boolean',
                '"created_at" timestamp with time zone',
            ],
            [],  # Master has no dependencies (empty state)
            [
                ("r:test_schema.complex_table", "test_schema"),
            ],
        ),
        # Empty database (no-op case)
        (
            None,
            None,
            "empty database",
            [],  # No SQL terms
            [],  # Master has no dependencies (empty state)
            [],  # Branch has no dependencies (empty state)
        ),
        # Schema only
        (
            None,
            "CREATE SCHEMA empty_schema;",
            "schema only",
            [
                'CREATE SCHEMA "empty_schema"',
            ],
            [],  # Master has no dependencies (empty state)
            [],  # Branch has no dependencies (just schema)
        ),
        # E-commerce scenario with sequences, tables, constraints, indexes
        (
            None,
            """
            CREATE SCHEMA ecommerce;

            -- Create customers table with SERIAL primary key
            CREATE TABLE ecommerce.customers (
                id SERIAL PRIMARY KEY,
                email VARCHAR(255) UNIQUE NOT NULL,
                first_name VARCHAR(100) NOT NULL,
                last_name VARCHAR(100) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            -- Create orders table with SERIAL primary key and foreign key
            CREATE TABLE ecommerce.orders (
                id SERIAL PRIMARY KEY,
                customer_id INTEGER NOT NULL,
                order_number VARCHAR(50) UNIQUE NOT NULL,
                status VARCHAR(20) DEFAULT 'pending',
                total_amount DECIMAL(10,2) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT fk_customer FOREIGN KEY (customer_id) REFERENCES ecommerce.customers(id)
            );

            -- Create index for common queries
            CREATE INDEX idx_orders_customer_status ON ecommerce.orders(customer_id, status);
            CREATE INDEX idx_customers_email ON ecommerce.customers(email);
            """,
            "e-commerce with sequences, tables, constraints, and indexes",
            [
                'CREATE SCHEMA "ecommerce"',
                "CREATE SEQUENCE",
                'CREATE TABLE "ecommerce"."customers"',
                'CREATE TABLE "ecommerce"."orders"',
                "customers_id_seq",
                "orders_id_seq",
                "customers_pkey",
                "orders_pkey",
                "customers_email_key",
                "orders_order_number_key",
                "fk_customer",
                "idx_orders_customer_status",
                "idx_customers_email",
                "OWNED BY",
                "FOREIGN KEY",
            ],
            [],  # Master has no dependencies (empty state)
            [
                # Schema dependencies
                ("r:ecommerce.customers", "ecommerce"),
                ("r:ecommerce.orders", "ecommerce"),
                ("S:ecommerce.customers_id_seq", "ecommerce"),
                ("S:ecommerce.orders_id_seq", "ecommerce"),
                # Sequence ownership dependencies (sequences owned by tables)
                ("S:ecommerce.customers_id_seq", "r:ecommerce.customers"),
                ("S:ecommerce.orders_id_seq", "r:ecommerce.orders"),
                # Constraint dependencies
                ("ecommerce.customers.customers_pkey", "r:ecommerce.customers"),
                ("ecommerce.customers.customers_email_key", "r:ecommerce.customers"),
                ("ecommerce.orders.orders_pkey", "r:ecommerce.orders"),
                ("ecommerce.orders.orders_order_number_key", "r:ecommerce.orders"),
                ("ecommerce.orders.fk_customer", "r:ecommerce.orders"),
                ("ecommerce.orders.fk_customer", "r:ecommerce.customers"),
                ("ecommerce.orders.fk_customer", "i:ecommerce.customers_pkey"),
                # Index dependencies (indexes depend on their underlying constraints/tables)
                ("i:ecommerce.customers_pkey", "ecommerce.customers.customers_pkey"),
                (
                    "i:ecommerce.customers_email_key",
                    "ecommerce.customers.customers_email_key",
                ),
                ("i:ecommerce.orders_pkey", "ecommerce.orders.orders_pkey"),
                (
                    "i:ecommerce.orders_order_number_key",
                    "ecommerce.orders.orders_order_number_key",
                ),
                ("i:ecommerce.idx_customers_email", "r:ecommerce.customers"),
                ("i:ecommerce.idx_orders_customer_status", "r:ecommerce.orders"),
            ],
        ),
        # Complex dependency ordering - moved from test_dependency_cycles.py
        (
            "CREATE SCHEMA test_schema",
            """
            -- Create base tables
            CREATE TABLE test_schema.users (
                id integer PRIMARY KEY,
                name text
            );

            CREATE TABLE test_schema.orders (
                id integer PRIMARY KEY,
                user_id integer,
                amount numeric
            );

            -- Create view that depends on both tables
            CREATE VIEW test_schema.user_orders AS
                SELECT u.id, u.name, SUM(o.amount) as total
                FROM test_schema.users u
                LEFT JOIN test_schema.orders o ON u.id = o.user_id
                GROUP BY u.id, u.name;

            -- Create view that depends on the first view
            CREATE VIEW test_schema.top_users AS
                SELECT * FROM test_schema.user_orders
                WHERE total > 1000;
            """,
            "complex dependency ordering",
            [
                'CREATE TABLE "test_schema"."users"',
                'CREATE TABLE "test_schema"."orders"',
                'CREATE VIEW "test_schema"."user_orders"',
                'CREATE VIEW "test_schema"."top_users"',
            ],
            [],
            [
                ("r:test_schema.users", "test_schema"),
                ("r:test_schema.orders", "test_schema"),
                (
                    "test_schema.users.users_pkey",
                    "r:test_schema.users",
                ),  # PK constraint depends on table
                (
                    "test_schema.orders.orders_pkey",
                    "r:test_schema.orders",
                ),  # PK constraint depends on table
                (
                    "i:test_schema.users_pkey",
                    "test_schema.users.users_pkey",
                ),  # Index depends on PK constraint
                (
                    "i:test_schema.orders_pkey",
                    "test_schema.orders.orders_pkey",
                ),  # Index depends on PK constraint
                ("v:test_schema.user_orders", "r:test_schema.users"),
                ("v:test_schema.user_orders", "r:test_schema.orders"),
                ("v:test_schema.user_orders", "test_schema"),
                ("v:test_schema.top_users", "v:test_schema.user_orders"),
                ("v:test_schema.top_users", "test_schema"),
            ],
        ),
        # Drop operations with complex dependencies - moved from test_dependency_edge_cases.py
        (
            """
            CREATE SCHEMA test_schema;

            -- Create a complex dependency chain
            CREATE TABLE test_schema.base (
                id integer PRIMARY KEY
            );

            CREATE VIEW test_schema.v1 AS SELECT * FROM test_schema.base;
            CREATE VIEW test_schema.v2 AS SELECT * FROM test_schema.v1;
            CREATE VIEW test_schema.v3 AS SELECT * FROM test_schema.v2;
            """,
            """
            -- Drop everything to test dependency ordering
            DROP VIEW test_schema.v3;
            DROP VIEW test_schema.v2;
            DROP VIEW test_schema.v1;
            DROP TABLE test_schema.base;
            DROP SCHEMA test_schema;
            """,
            "drop operations with complex dependencies",
            [
                'DROP VIEW "test_schema"."v3"',
                'DROP VIEW "test_schema"."v2"',
                'DROP VIEW "test_schema"."v1"',
                'DROP TABLE "test_schema"."base"',
                'DROP SCHEMA "test_schema"',
            ],
            [
                ("r:test_schema.base", "test_schema"),
                (
                    "test_schema.base.base_pkey",
                    "r:test_schema.base",
                ),  # PK constraint depends on table
                (
                    "i:test_schema.base_pkey",
                    "test_schema.base.base_pkey",
                ),  # Index depends on PK constraint
                ("v:test_schema.v1", "r:test_schema.base"),
                ("v:test_schema.v1", "test_schema"),
                ("v:test_schema.v2", "v:test_schema.v1"),
                ("v:test_schema.v2", "test_schema"),
                ("v:test_schema.v3", "v:test_schema.v2"),
                ("v:test_schema.v3", "test_schema"),
            ],
            [],  # Branch has no dependencies (everything dropped)
        ),
        # Mixed create and replace operations - moved from test_dependency_edge_cases.py
        (
            """
            CREATE SCHEMA test_schema;

            CREATE TABLE test_schema.data (
                id integer PRIMARY KEY,
                value text
            );

            CREATE VIEW test_schema.summary AS
                SELECT COUNT(*) as cnt FROM test_schema.data;
            """,
            """
            -- Add column and update view
            ALTER TABLE test_schema.data ADD COLUMN status text;

            CREATE OR REPLACE VIEW test_schema.summary AS
                SELECT COUNT(*) as cnt,
                       COUNT(CASE WHEN status = 'active' THEN 1 END) as active_cnt
                FROM test_schema.data;
            """,
            "mixed create and replace operations",
            [
                'ALTER TABLE "test_schema"."data" ADD COLUMN "status"',
                'CREATE OR REPLACE VIEW "test_schema"."summary"',
            ],
            [
                ("r:test_schema.data", "test_schema"),
                (
                    "test_schema.data.data_pkey",
                    "r:test_schema.data",
                ),  # PK constraint depends on table
                (
                    "i:test_schema.data_pkey",
                    "test_schema.data.data_pkey",
                ),  # Index depends on PK constraint
                ("v:test_schema.summary", "r:test_schema.data"),
                ("v:test_schema.summary", "test_schema"),
            ],
            [
                ("r:test_schema.data", "test_schema"),
                (
                    "test_schema.data.data_pkey",
                    "r:test_schema.data",
                ),  # PK constraint depends on table
                (
                    "i:test_schema.data_pkey",
                    "test_schema.data.data_pkey",
                ),  # Index depends on PK constraint
                ("v:test_schema.summary", "r:test_schema.data"),
                ("v:test_schema.summary", "test_schema"),
            ],
        ),
        # Cross-schema view dependencies - moved from test_dependency_edge_cases.py
        (
            """
            CREATE SCHEMA schema_a;
            CREATE SCHEMA schema_b;

            CREATE TABLE schema_a.table_a (id integer PRIMARY KEY);
            CREATE TABLE schema_b.table_b (id integer PRIMARY KEY);

            -- View in schema_a that references table in schema_b
            CREATE VIEW schema_a.cross_view AS
                SELECT a.id as a_id, b.id as b_id
                FROM schema_a.table_a a
                CROSS JOIN schema_b.table_b b;
            """,
            "",  # No changes - just test dependency extraction
            "cross-schema view dependencies",
            [],  # No SQL expected since no changes
            [
                ("r:schema_a.table_a", "schema_a"),
                ("r:schema_b.table_b", "schema_b"),
                (
                    "schema_a.table_a.table_a_pkey",
                    "r:schema_a.table_a",
                ),  # PK constraint depends on table
                (
                    "schema_b.table_b.table_b_pkey",
                    "r:schema_b.table_b",
                ),  # PK constraint depends on table
                (
                    "i:schema_a.table_a_pkey",
                    "schema_a.table_a.table_a_pkey",
                ),  # Index depends on PK constraint
                (
                    "i:schema_b.table_b_pkey",
                    "schema_b.table_b.table_b_pkey",
                ),  # Index depends on PK constraint
                ("v:schema_a.cross_view", "r:schema_a.table_a"),
                ("v:schema_a.cross_view", "r:schema_b.table_b"),
                ("v:schema_a.cross_view", "schema_a"),
            ],
            [
                ("r:schema_a.table_a", "schema_a"),
                ("r:schema_b.table_b", "schema_b"),
                (
                    "schema_a.table_a.table_a_pkey",
                    "r:schema_a.table_a",
                ),  # PK constraint depends on table
                (
                    "schema_b.table_b.table_b_pkey",
                    "r:schema_b.table_b",
                ),  # PK constraint depends on table
                (
                    "i:schema_a.table_a_pkey",
                    "schema_a.table_a.table_a_pkey",
                ),  # Index depends on PK constraint
                (
                    "i:schema_b.table_b_pkey",
                    "schema_b.table_b.table_b_pkey",
                ),  # Index depends on PK constraint
                ("v:schema_a.cross_view", "r:schema_a.table_a"),
                ("v:schema_a.cross_view", "r:schema_b.table_b"),
                ("v:schema_a.cross_view", "schema_a"),
            ],
        ),
        # Basic dependency validation - table->schema dependency
        (
            None,
            """
            CREATE SCHEMA analytics;
            CREATE TABLE analytics.users (
                id integer,
                name text
            );
            """,
            "basic table schema dependency validation",
            [
                'CREATE SCHEMA "analytics"',
                'CREATE TABLE "analytics"."users"',
            ],
            [],  # Master has no dependencies (empty state)
            [
                ("r:analytics.users", "analytics"),
            ],
        ),
        # Multiple independent schema+table pairs
        (
            None,
            """
            CREATE SCHEMA app;
            CREATE SCHEMA analytics;
            CREATE TABLE app.users (id integer);
            CREATE TABLE analytics.reports (id integer);
            """,
            "multiple independent schema table pairs",
            [
                'CREATE SCHEMA "app"',
                'CREATE SCHEMA "analytics"',
                'CREATE TABLE "app"."users"',
                'CREATE TABLE "analytics"."reports"',
            ],
            [],  # Master has no dependencies (empty state)
            [
                ("r:app.users", "app"),
                ("r:analytics.reports", "analytics"),
            ],
        ),
        # DROP schema only
        (
            """
            CREATE SCHEMA temp_schema;
            """,
            """
            DROP SCHEMA temp_schema;
            """,
            "drop schema only",
            [
                'DROP SCHEMA "temp_schema"',
            ],
            [],  # Master dependencies (temp_schema exists)
            [],  # Branch has no dependencies (schema dropped)
        ),
        # Multiple DROP operations with dependency ordering
        (
            """
            CREATE SCHEMA app;
            CREATE SCHEMA analytics;
            CREATE TABLE app.users (id integer);
            CREATE TABLE analytics.reports (id integer);
            """,
            """
            DROP TABLE app.users;
            DROP TABLE analytics.reports;
            DROP SCHEMA app;
            DROP SCHEMA analytics;
            """,
            "multiple drops with dependency ordering",
            [
                'DROP TABLE "app"."users"',
                'DROP TABLE "analytics"."reports"',
                'DROP SCHEMA "app"',
                'DROP SCHEMA "analytics"',
            ],
            [
                ("r:app.users", "app"),
                ("r:analytics.reports", "analytics"),
            ],  # Master dependencies (objects exist before drop)
            [],  # Branch has no dependencies (everything dropped)
        ),
        # Complex multi-schema drop scenario
        (
            """
            CREATE SCHEMA core;
            CREATE SCHEMA analytics;
            CREATE SCHEMA reporting;
            CREATE TABLE core.users (id integer);
            CREATE TABLE analytics.events (id integer);
            CREATE TABLE reporting.summary (id integer);
            """,
            """
            DROP TABLE core.users;
            DROP TABLE analytics.events;
            DROP TABLE reporting.summary;
            DROP SCHEMA core;
            DROP SCHEMA analytics;
            DROP SCHEMA reporting;
            """,
            "complex multi-schema drop scenario",
            [
                'DROP TABLE "core"."users"',
                'DROP TABLE "analytics"."events"',
                'DROP TABLE "reporting"."summary"',
                'DROP SCHEMA "core"',
                'DROP SCHEMA "analytics"',
                'DROP SCHEMA "reporting"',
            ],
            [
                ("r:core.users", "core"),
                ("r:analytics.events", "analytics"),
                ("r:reporting.summary", "reporting"),
            ],  # Master dependencies (objects exist before drop)
            [],  # Branch has no dependencies (everything dropped)
        ),
    ],
    ids=[
        "schema_and_table_creation",
        "multiple_schemas_and_tables",
        "complex_column_types",
        "empty_database",
        "schema_only",
        "ecommerce_with_sequences_and_constraints",
        "complex_dependency_ordering",
        "drop_operations_with_complex_dependencies",
        "mixed_create_and_replace_operations",
        "cross_schema_view_dependencies",
        "basic_table_schema_dependency_validation",
        "multiple_independent_schema_table_pairs",
        "drop_schema_only",
        "multiple_drops_with_dependency_ordering",
        "complex_multi_schema_drop_scenario",
    ],
)
def test_mixed_objects_roundtrip(
    session,
    alt_session,
    initial_setup,
    test_sql,
    description,
    expected_sql_terms,
    expected_master_dependencies,
    expected_branch_dependencies,
):
    """Test complete pipeline with various database object combinations."""
    roundtrip_fidelity_test(
        master_session=session,
        branch_session=alt_session,
        initial_setup=initial_setup,
        test_sql=test_sql,
        description=description,
        expected_sql_terms=expected_sql_terms,
        expected_master_dependencies=expected_master_dependencies,
        expected_branch_dependencies=expected_branch_dependencies,
    )
