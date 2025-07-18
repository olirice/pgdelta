"""Integration tests for constraint operations.

These tests verify full end-to-end constraint functionality including
diff engine detection, SQL generation, and roundtrip fidelity.
"""

import pytest
from tests.integration.roundtrip import roundtrip_fidelity_test


@pytest.mark.parametrize(
    "test_name,initial_setup,test_sql,expected_terms,expected_master_dependencies,expected_branch_dependencies",
    [
        (
            "add primary key constraint",
            """
            CREATE SCHEMA test_schema;
            CREATE TABLE test_schema.users (
                id integer NOT NULL,
                email character varying(255) NOT NULL
            );
            """,
            """
            ALTER TABLE test_schema.users ADD CONSTRAINT users_pkey PRIMARY KEY (id);
            """,
            [
                'ALTER TABLE "test_schema"."users" ADD CONSTRAINT "users_pkey" PRIMARY KEY',
                '"id"',  # Real column name
            ],
            [
                ("r:test_schema.users", "test_schema"),  # Table depends on schema
            ],
            [
                (
                    "test_schema.users.users_pkey",
                    "r:test_schema.users",
                ),  # Constraint depends on table
                (
                    "i:test_schema.users_pkey",
                    "test_schema.users.users_pkey",
                ),  # Index depends on constraint
                ("r:test_schema.users", "test_schema"),  # Table depends on schema
            ],
        ),
        (
            "add unique constraint",
            """
            CREATE SCHEMA test_schema;
            CREATE TABLE test_schema.users (
                id integer NOT NULL,
                email character varying(255) NOT NULL
            );
            """,
            """
            ALTER TABLE test_schema.users ADD CONSTRAINT users_email_key UNIQUE (email);
            """,
            [
                'ALTER TABLE "test_schema"."users" ADD CONSTRAINT "users_email_key" UNIQUE',
                '"email"',  # Real column name
            ],
            [
                ("r:test_schema.users", "test_schema"),  # Table depends on schema
            ],
            [
                ("test_schema.users.users_email_key", "r:test_schema.users"),
                (
                    "i:test_schema.users_email_key",
                    "test_schema.users.users_email_key",
                ),  # Index depends on constraint
                ("r:test_schema.users", "test_schema"),  # Table depends on schema
            ],
        ),
        (
            "add check constraint",
            """
            CREATE SCHEMA test_schema;
            CREATE TABLE test_schema.products (
                id integer NOT NULL,
                price numeric(10,2) NOT NULL
            );
            """,
            """
            ALTER TABLE test_schema.products ADD CONSTRAINT products_price_check CHECK (price > 0);
            """,
            [
                'ALTER TABLE "test_schema"."products" ADD CONSTRAINT "products_price_check" CHECK',
                "(price > (0)::numeric)",
            ],
            [
                ("r:test_schema.products", "test_schema"),  # Table depends on schema
            ],
            [
                ("test_schema.products.products_price_check", "r:test_schema.products"),
                ("r:test_schema.products", "test_schema"),  # Table depends on schema
            ],
        ),
        (
            "add foreign key constraint",
            """
            CREATE SCHEMA test_schema;
            CREATE TABLE test_schema.users (
                id integer NOT NULL,
                email character varying(255) NOT NULL,
                CONSTRAINT users_pkey PRIMARY KEY (id)
            );
            CREATE TABLE test_schema.orders (
                id integer NOT NULL,
                user_id integer NOT NULL
            );
            """,
            """
            ALTER TABLE test_schema.orders ADD CONSTRAINT orders_user_id_fkey
                FOREIGN KEY (user_id) REFERENCES test_schema.users (id) ON DELETE CASCADE;
            """,
            [
                'ALTER TABLE "test_schema"."orders" ADD CONSTRAINT "orders_user_id_fkey" FOREIGN KEY',
                '"user_id"',  # Real local column name
                'REFERENCES "test_schema"."users"',
                '"id"',  # Real referenced column name
                "ON DELETE CASCADE",
            ],
            [
                (
                    "test_schema.users.users_pkey",
                    "r:test_schema.users",
                ),  # PK constraint from setup
                (
                    "i:test_schema.users_pkey",
                    "test_schema.users.users_pkey",
                ),  # Index depends on PK constraint
                ("r:test_schema.orders", "test_schema"),  # Table depends on schema
                ("r:test_schema.users", "test_schema"),  # Table depends on schema
            ],
            [
                ("test_schema.orders.orders_user_id_fkey", "r:test_schema.orders"),
                (
                    "test_schema.orders.orders_user_id_fkey",
                    "r:test_schema.users",
                ),  # FK depends on referenced table
                (
                    "test_schema.orders.orders_user_id_fkey",
                    "i:test_schema.users_pkey",
                ),  # FK depends on referenced index
                (
                    "test_schema.users.users_pkey",
                    "r:test_schema.users",
                ),  # PK constraint from setup
                (
                    "i:test_schema.users_pkey",
                    "test_schema.users.users_pkey",
                ),  # Index depends on PK constraint
                ("r:test_schema.orders", "test_schema"),  # Table depends on schema
                ("r:test_schema.users", "test_schema"),  # Table depends on schema
            ],
        ),
        (
            "drop primary key constraint",
            """
            CREATE SCHEMA test_schema;
            CREATE TABLE test_schema.users (
                id integer NOT NULL,
                email character varying(255) NOT NULL,
                CONSTRAINT users_pkey PRIMARY KEY (id)
            );
            """,
            """
            ALTER TABLE test_schema.users DROP CONSTRAINT users_pkey;
            """,
            [
                'ALTER TABLE "test_schema"."users" DROP CONSTRAINT "users_pkey"',
            ],
            [
                ("test_schema.users.users_pkey", "r:test_schema.users"),
                (
                    "i:test_schema.users_pkey",
                    "test_schema.users.users_pkey",
                ),  # Index depends on constraint
                ("r:test_schema.users", "test_schema"),  # Table depends on schema
            ],
            [
                ("r:test_schema.users", "test_schema"),  # Table depends on schema
            ],
        ),
        (
            "drop unique constraint",
            """
            CREATE SCHEMA test_schema;
            CREATE TABLE test_schema.users (
                id integer NOT NULL,
                email character varying(255) NOT NULL,
                CONSTRAINT users_email_key UNIQUE (email)
            );
            """,
            """
            ALTER TABLE test_schema.users DROP CONSTRAINT users_email_key;
            """,
            [
                'ALTER TABLE "test_schema"."users" DROP CONSTRAINT "users_email_key"',
            ],
            [
                ("test_schema.users.users_email_key", "r:test_schema.users"),
                (
                    "i:test_schema.users_email_key",
                    "test_schema.users.users_email_key",
                ),  # Index depends on constraint
                ("r:test_schema.users", "test_schema"),  # Table depends on schema
            ],
            [
                ("r:test_schema.users", "test_schema"),  # Table depends on schema
            ],
        ),
        (
            "drop check constraint",
            """
            CREATE SCHEMA test_schema;
            CREATE TABLE test_schema.products (
                id integer NOT NULL,
                price numeric(10,2) NOT NULL,
                CONSTRAINT products_price_check CHECK (price > 0)
            );
            """,
            """
            ALTER TABLE test_schema.products DROP CONSTRAINT products_price_check;
            """,
            [
                'ALTER TABLE "test_schema"."products" DROP CONSTRAINT "products_price_check"',
            ],
            [
                ("test_schema.products.products_price_check", "r:test_schema.products"),
                ("r:test_schema.products", "test_schema"),  # Table depends on schema
            ],
            [
                ("r:test_schema.products", "test_schema"),  # Table depends on schema
            ],
        ),
        (
            "drop foreign key constraint",
            """
            CREATE SCHEMA test_schema;
            CREATE TABLE test_schema.users (
                id integer NOT NULL,
                CONSTRAINT users_pkey PRIMARY KEY (id)
            );
            CREATE TABLE test_schema.orders (
                id integer NOT NULL,
                user_id integer NOT NULL,
                CONSTRAINT orders_user_id_fkey FOREIGN KEY (user_id) REFERENCES test_schema.users (id)
            );
            """,
            """
            ALTER TABLE test_schema.orders DROP CONSTRAINT orders_user_id_fkey;
            """,
            [
                'ALTER TABLE "test_schema"."orders" DROP CONSTRAINT "orders_user_id_fkey"',
            ],
            [
                ("test_schema.orders.orders_user_id_fkey", "r:test_schema.orders"),
                (
                    "test_schema.orders.orders_user_id_fkey",
                    "r:test_schema.users",
                ),  # FK depends on referenced table
                (
                    "test_schema.orders.orders_user_id_fkey",
                    "i:test_schema.users_pkey",
                ),  # FK depends on referenced index
                (
                    "test_schema.users.users_pkey",
                    "r:test_schema.users",
                ),  # PK constraint from setup
                (
                    "i:test_schema.users_pkey",
                    "test_schema.users.users_pkey",
                ),  # Index depends on PK constraint
                ("r:test_schema.orders", "test_schema"),  # Table depends on schema
                ("r:test_schema.users", "test_schema"),  # Table depends on schema
            ],
            [
                (
                    "test_schema.users.users_pkey",
                    "r:test_schema.users",
                ),  # PK constraint from setup
                (
                    "i:test_schema.users_pkey",
                    "test_schema.users.users_pkey",
                ),  # Index depends on PK constraint
                ("r:test_schema.orders", "test_schema"),  # Table depends on schema
                ("r:test_schema.users", "test_schema"),  # Table depends on schema
            ],
        ),
        (
            "add multiple constraints to same table",
            """
            CREATE SCHEMA test_schema;
            CREATE TABLE test_schema.users (
                id integer NOT NULL,
                email character varying(255) NOT NULL,
                age integer
            );
            """,
            """
            ALTER TABLE test_schema.users ADD CONSTRAINT users_pkey PRIMARY KEY (id);
            ALTER TABLE test_schema.users ADD CONSTRAINT users_email_key UNIQUE (email);
            ALTER TABLE test_schema.users ADD CONSTRAINT users_age_check CHECK (age >= 0);
            """,
            [
                'ALTER TABLE "test_schema"."users" ADD CONSTRAINT "users_pkey" PRIMARY KEY',
                'ALTER TABLE "test_schema"."users" ADD CONSTRAINT "users_email_key" UNIQUE',
                'ALTER TABLE "test_schema"."users" ADD CONSTRAINT "users_age_check" CHECK',
                "(age >= 0)",
            ],
            [
                ("r:test_schema.users", "test_schema"),  # Table depends on schema
            ],
            [
                ("test_schema.users.users_pkey", "r:test_schema.users"),
                ("test_schema.users.users_email_key", "r:test_schema.users"),
                ("test_schema.users.users_age_check", "r:test_schema.users"),
                (
                    "i:test_schema.users_pkey",
                    "test_schema.users.users_pkey",
                ),  # Index depends on PK constraint
                (
                    "i:test_schema.users_email_key",
                    "test_schema.users.users_email_key",
                ),  # Index depends on UNIQUE constraint
                ("r:test_schema.users", "test_schema"),  # Table depends on schema
            ],
        ),
        (
            "constraint with special characters in names",
            """
            CREATE SCHEMA "my-schema";
            CREATE TABLE "my-schema"."my-table" (
                id integer NOT NULL,
                "my-field" text
            );
            """,
            """
            ALTER TABLE "my-schema"."my-table" ADD CONSTRAINT "my-table_check$constraint"
                CHECK ("my-field" IS NOT NULL);
            """,
            [
                'ALTER TABLE "my-schema"."my-table" ADD CONSTRAINT "my-table_check$constraint" CHECK',
                '"my-field" IS NOT NULL',
            ],
            [
                ("r:my-schema.my-table", "my-schema"),  # Table depends on schema
            ],
            [
                (
                    "my-schema.my-table.my-table_check$constraint",
                    "r:my-schema.my-table",
                ),
                ("r:my-schema.my-table", "my-schema"),  # Table depends on schema
            ],
        ),
    ],
)
@pytest.mark.integration
def test_constraint_operations(
    session,
    alt_session,
    test_name: str,
    initial_setup: str,
    test_sql: str,
    expected_terms: list[str],
    expected_master_dependencies: list[tuple[str, str]],
    expected_branch_dependencies: list[tuple[str, str]],
):
    """Test constraint operations with full roundtrip fidelity."""
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
